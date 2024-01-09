import argparse
import tqdm
from game import Q20Game
import openai
import os
import logging
from utils import boolean_string, load_model


# Set up OpenAI API credentials
openai.api_key = os.environ["OPENAI_API_KEY"]
LOGGER = logging.getLogger(__name__)

def run_chat(args, item, guesser_model=None, guesser_tokenizer=None):
    if not args.openai_api:
        guesser_kargs = {
            "max_new_tokens": 64,
            "temperature": args.temp,
            "repetition_penalty": 1.0,
            "do_sample": True,
        }  # no penalty
    else:
        guesser_model = args.guesser_model
        guesser_kargs = {}
    game = Q20Game(
        item=item,
        answerer_model=args.answerer_model,
        guesser_model=guesser_model,
        guesser_tokenizer=guesser_tokenizer,
        num_turns=args.turns,
        temperature=args.temp,
        openai_api=args.openai_api,
        guesser_kargs=guesser_kargs,
    )

    for s in tqdm.tqdm(
        range(args.num_sessions), desc=f"Playing {item} for {args.num_sessions} times"
    ):
        file_name = os.path.join(
            os.path.dirname(args.input),
            args.guesser_model + f"_{args.suffix}",
            f"_session_{s}" if args.num_sessions > 1 else "",
        )
        if not os.path.exists(os.path.join(file_name, f"{item}.txt")):
            game.game_play(user_mode=args.user)
            game.save_session(path=file_name)
        else:
            LOGGER.info(
                f"Skipping {item}, session {s} because it was found in output dir"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Q20 game")
    # Add an argument for the input file
    parser.add_argument("--input", required=True, help="Input file path")
    parser.add_argument(
        "--answerer_model", "-a", default="gpt-3.5-turbo", help="answerer model"
    )
    parser.add_argument(
        "--guesser_model", "-g", default="gpt-3.5-turbo", help="guesser model"
    )
    parser.add_argument("--suffix", "-s", default="vanilla", help="prefix")
    parser.add_argument("--user", default=None, help="User name for user mode")
    parser.add_argument("--turns", type=int, default=20, help="Set the maximum number of turns for the game")
    parser.add_argument("--temp", type=float, default=0.8, help="Temperature")
    parser.add_argument("--num-sessions", type=int, default=1, help="Num of sessions")
    parser.add_argument(
        "--openai-api",
        type=boolean_string,
        default="True",
        help="Use OpenAI API server for the guesser model"
    )
    # Parse the command-line arguments
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f_input:
        item_list = [l.strip() for l in f_input.readlines()]
    if args.user is None:
        if (not args.openai_api) and "/" in args.guesser_model:
            guesser_model, guesser_tokenizer = load_model(args.guesser_model)
        else:
            guesser_model, guesser_tokenizer = None, None

        for item in tqdm.tqdm(item_list, desc="Playing Games"):
            run_chat(args, item, guesser_model, guesser_tokenizer)

    else:
        for i, item in enumerate(item_list):
            print(f"\n\n*************** GAME {i} *************** \n\n")
            run_chat(args, item)
            print(f"\n\nAnswer: {item}")
