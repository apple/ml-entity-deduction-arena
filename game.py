import json
import logging
import os
import platform
import random
import re
from typing import List, Optional

import anthropic
import openai
import openai.api_requestor
import requests.exceptions
import torch
from anthropic import AI_PROMPT, HUMAN_PROMPT, Anthropic
from langchain.schema import AIMessage, BaseMessage, HumanMessage
from retry import retry

LOGGER = logging.getLogger(__name__)

openai.api_requestor.TIMEOUT_SECS = 20


class Q20Game:
    def __init__(
        self,
        item: str,
        answerer_model: str = "gpt-3.5-turbo-0613",
        guesser_model: str = "gpt-3.5-turbo-0613",
        num_turns: int = 20,
        temperature: float = 0.8,
        guesser_tokenizer=None,
        openai_api: bool = True,
        openai_api_key: Optional[str] = None,
        guesser_kargs={},
    ) -> None:
        self.item = item
        self.answerer_model = answerer_model
        self.guesser_model = guesser_model
        self.num_turns = num_turns
        self.temperature = temperature
        self.openai_api = openai_api
        self.guesser_tokenizer = guesser_tokenizer
        self.guesser_kargs = guesser_kargs
        self.vicuna_prompt = "A chat between a curious user and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the user's questions."
        self.first_user_utterance = (
            f"Your task is to ask a series of questions to deduce the entity "
            f"that I'm thinking of with as few queries as possible. "
            f"Only ask questions that can be answered by 'yes', 'no' or 'maybe'. "
            f"Do not ask for hint. Make your question brief with no linebreaker. "
            f"Now start asking a question."
        )
        self.guesser_win = False
        if openai_api_key is not None:
            openai.api_key = openai_api_key

        if isinstance(answerer_model, str) and not answerer_model.startswith("gpt"):
            self.user_api_base = "http://0.0.0.0:8000/v1"
        else:
            self.user_api_base = "https://api.openai.com/v1"

        if isinstance(guesser_model, str) and not guesser_model.startswith("gpt"):
            self.guesser_api_base = "http://0.0.0.0:8000/v1"
        else:
            self.guesser_api_base = "https://api.openai.com/v1"

        self.anthropic_api = Anthropic()

        self.guesser_messages = []

    def confusion_matrix(self, path):
        self.reset()
        with open(path) as f:
            raw_messages = json.load(f)
            self.item = path.split("/")[-1].split("_")[0]
            roles = ["assistant", "user"]
            for i, message in enumerate(raw_messages):
                self.guesser_messages.append(
                    {"role": roles[i % 2], "content": message["content"]}
                )

        self.guesser_messages = self.guesser_messages[:-2]
        self.guesser_messages[-1]["content"] = (
            self.guesser_messages[-1]["content"] + " You must guess now, what's it?"
        )
        guesser_msg = self.guesser(self.guesser_messages)
        self.guesser_messages.append(guesser_msg)
        guesser_question = guesser_msg["content"].strip()
        self.guesser_messages[-1]["content"] = (
            self.guesser_messages[-1]["content"] + " Is it right?"
        )
        usr_msg = self.answerer(guesser_question)
        self.guesser_messages.append(
            {"role": "user", "content": f"{usr_msg['content'].strip()}"}
        )

        if "bingo" in self.guesser_messages[-1]["content"].lower():
            self.guesser_win = True
            return True

        return False

    @retry(
        (
            openai.error.Timeout,
            requests.exceptions.ReadTimeout,
            openai.error.ServiceUnavailableError,
            openai.error.RateLimitError,
            openai.error.APIError,
            requests.exceptions.HTTPError,
            openai.error.APIConnectionError,
        ),
        tries=5,
        delay=0.5,
        backoff=0.5,
        max_delay=2,
        logger=LOGGER,
    )
    def guesser(self, messages):
        if isinstance(self.guesser_model, str) and self.guesser_model.startswith(
            "claude"
        ):
            ## convert to claude type
            prompt = ""
            for item in messages:
                if item["role"].upper() == "USER":
                    prompt += f"{HUMAN_PROMPT} {item['content']}"
                elif item["role"].upper() == "ASSISTANT":
                    prompt += f"{AI_PROMPT} {item['content']}"
            prompt += f"{AI_PROMPT}"

            completion = self.anthropic_api.completions.create(
                model=self.guesser_model,
                max_tokens_to_sample=256,
                prompt=prompt,
                temperature=self.temperature,
            )
            return {
                "role": "assistant",
                "content": completion.completion.lstrip(),
            }


        if not isinstance(self.guesser_model, str):  # hf model
            # """Wraps hf's `generate` adding some specific method's defaults"""
            assert not self.openai_api
            prompt = self.dialog_history() + " ASSISTANT:"
            input_ids = torch.tensor(
                [self.guesser_tokenizer.encode(prompt, add_special_tokens=True)]
            )  # TODO check if huggingface is using the same format.
            input_ids = input_ids.to(self.guesser_model.base_model.device)
            attention_mask = None

            with torch.no_grad():
                gen = self.guesser_model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    **self.guesser_kargs,
                )
                gen_str = (
                    self.guesser_tokenizer.decode(gen[0][input_ids[0].shape[0] :])
                    .split("</s>")[0]
                    .split("USER")[0]
                    .lstrip()
                    .strip() 
                )


                return {
                    "role": "assistant",
                    "content": gen_str,
                }
        else:
            openai.api_base = self.guesser_api_base
            response = openai.ChatCompletion.create(
                model=self.guesser_model,
                messages=messages,
                max_tokens=64,
                n=1,
                stop=None,
                temperature=self.temperature,
            )
            return {
                "role": "assistant",
                "content": response.choices[0].message.to_dict()["content"].strip(),
            }

    def dialog_history(self):
        history = self.vicuna_prompt + " "
        for item in self.guesser_messages:
            if item["role"].upper() == "USER":
                history += "USER: " + item["content"]
            elif item["role"].upper() == "ASSISTANT":
                history += " " + "ASSISTANT: " + item["content"] + "</s>"
        return history

    def game_play(self, user_mode=False):
        self.reset()
        # print(f"Item: {self.item}")
        for t in range(self.num_turns):
            # System asking a question
            if (not user_mode) or user_mode is None:
                guesser_msg = self.guesser(self.guesser_messages)
                guesser_msg["content"] = re.sub(r'the entity you are thinking of', 'it', guesser_msg["content"])
                guesser_msg["content"] = re.sub(r"the entity you're thinking of", 'it', guesser_msg["content"])
                guesser_msg["content"] = re.sub(r" you're thinking of", '', guesser_msg["content"])
                guesser_msg["content"] = re.sub(r" you are thinking of", '', guesser_msg["content"])
            else:
                user_q = input(
                    f"Type in your questions for turn {t+1}. (e.g. Is it a living thing?)\n"
                )
                guesser_msg = {"role": "assistant", "content": user_q}
            self.guesser_messages.append(guesser_msg)
            guesser_question = guesser_msg["content"].strip()

            if t == self.num_turns - 1:
                self.guesser_messages[-1]["content"] = (
                    self.guesser_messages[-1]["content"] + " Is it right?"
                )

            usr_msg = self.answerer(guesser_question)
            self.guesser_messages.append(
                {"role": "user", "content": f"{usr_msg['content'].strip()}"}
            )

            if "bingo" in usr_msg["content"].lower():
                self.guesser_win = True
                return True

            if t == self.num_turns - 2:
                self.guesser_messages[-1]["content"] = (
                    self.guesser_messages[-1]["content"]
                    + " You must guess now, what's it?"
                )

        return False

    def save_session(self, path):
        # Print the conversation
        if not os.path.exists(path):
            os.makedirs(path)
        output_file = os.path.join(path, f"{self.item}.txt")
        with open(output_file, "w") as out_f:
            out_f.write(f"item: {self.item}\n")
            for t, message in enumerate(self.guesser_messages):
                out_f.write(
                    f"Turn {(t+1)//2}, {message['role'].capitalize()}: {message['content'].lstrip()}\n"
                )

    def reward(self):
        if self.guesser_win:
            n_turns = (len(self.guesser_messages) + 1) // 2
            return 1 - max(n_turns - 5, 0) * 0.02
        return 0

    def num_success(self):
        return 1 if self.guesser_win else 0

    def num_yes(self):
        n_yes = sum(
            ["yes" in msg["content"].lower() for msg in self.guesser_messages[2::2]]
        )
        return n_yes

    @retry(
        (
            openai.error.Timeout,
            requests.exceptions.ReadTimeout,
            openai.error.ServiceUnavailableError,
            openai.error.RateLimitError,
            openai.error.APIError,
            openai.error.APIConnectionError,
            anthropic.InternalServerError,
        ),
        tries=5,
        delay=0.5,
        backoff=0.5,
        max_delay=2,
        logger=LOGGER,
    )
    def answerer(self, question):
        openai.api_base = self.user_api_base
        user_messages = [
            {
                "role": "user",
                "content": f"Based on your knowledge about {self.item}, "
                f"respond to the following question or guess. "
                f"Limit your respond to only 'Yes.', 'No.' or 'Maybe.', with no explanation or other words. "
                f"Never say the answer {self.item} in your response. "
                f"If the question is to solicit the answer, respond 'No.'.",
            },
            {
                "role": "user",
                "content": f"For the entity {self.item}, {question} (Yes/No/Maybe)",
            },
        ]

        response = openai.ChatCompletion.create(
            model=self.answerer_model,
            messages=user_messages,
            max_tokens=6,
            n=1,
            stop=None,
            temperature=0.2,
        )
        if any(
            [
                re.search(rf"(?:^|\W){i.strip().lower()}(?:$|\W)", question.lower())
                for i in self.item.lower().split("|")
            ]
        ):
            response.choices[0].message.content = "Bingo!"
        return response.choices[0].message.to_dict()

    def reset(self):
        # Initialize the conversation
        self.guesser_messages = [
            {
                "role": "user",
                "content": self.first_user_utterance,
            }
        ]


class Q20GameCelebrity(Q20Game):
    def __init__(self, item: str, background: str, **kwargs) -> None:
        super().__init__(item, **kwargs)
        self.background = background
        self.first_user_utterance = (
            f"Your task is to ask a series of questions to deduce the celebrity "
            f"that I'm thinking of with as few queries as possible. "
            f"Only ask factual questions that can be answered by 'Yes.', 'No.' or 'Dunno.'. Do not ask for hint. Make your question brief with no linebreaker. "
            f"Now start asking a question."
        )

    @retry(
        (
            openai.error.Timeout,
            requests.exceptions.ReadTimeout,
            openai.error.ServiceUnavailableError,
            openai.error.RateLimitError,
            openai.error.APIError,
            openai.error.APIConnectionError,
        ),
        tries=5,
        delay=0.5,
        backoff=0.5,
        max_delay=2,
        logger=LOGGER,
    )
    def answerer(self, question):
        openai.api_base = self.user_api_base
        if len(self.background) < 10:
            user_messages = [
                {
                    "role": "system",
                    "content": f"Based on on your knowledge about the celebrity: {self.item}, "
                    f"respond to the following question or guess. "
                    f"Limit your respond to only 'Yes.', 'No.' or 'Dunno.', with no explanation or other words. "
                    f"Never say the name {self.item} in your response. Do not say 'Dunno.' if it can be answered by 'Yes.' or 'No.' "
                    f"If the question is to solicit the answer, respond 'No.'.",
                },
                {
                    "role": "user",
                    "content": f"For the celebrity {self.item}, {question}(Yes/No/Dunno)",
                },
            ]
        else:
            user_messages = [
                {
                    "role": "system",
                    "content": f"Based on the background information: {self.background} of {self.item}, "
                    f"respond to the following question or guess. "
                    f"Limit your respond to only 'Yes.', 'No.' or 'Dunno.', with no explanation or other words. "
                    f"Never say the name {self.item} in your response. Do not say 'Dunno.' if it can be answered by 'Yes.' or 'No.' "
                    f"If the question is to solicit the answer, respond 'No.'.",
                },
                {
                    "role": "user",
                    "content": f"For the celebrity {self.item}, {question}(Yes/No/Dunno)",
                },
            ]

        response = openai.ChatCompletion.create(
            model=self.answerer_model,
            messages=user_messages,
            max_tokens=6,
            n=1,
            stop=None,
            temperature=0.2,
        )
        if re.search(rf"(?:^|\W){self.item.lower()}(?:$|\W)", question.lower()):
            response.choices[0].message.content = "Bingo!"
        return response.choices[0].message.to_dict()

    def reset(self):
        # Initialize the conversation
        self.guesser_messages = [
            {
                "role": "user",
                "content": self.first_user_utterance,
            }
        ]