# Entity-Deduction Arena (EDA) 

This software project accompanies the research paper, [Probing the Multi-turn Planning Capabilities of LLMs via 20 Question Games](https://arxiv.org/abs/2310.01468).

# Motivation

- There is a demand to assessing the capability of LLM to **clarify with questions** in order to effectively resolve ambiguities, when confronted with vague queries.
- This capability demands a sophisticated **understanding** of context, **state tracking**, **deductive reasoning**, and **strategic planning** across multiple conversational exchanges.

<p align = "center">
<img src="imgs/dialog.png" width="35%" alt="" align=center />
</p>

# Highlights

- The **Entity-Deduction Arena (EDA)** is a surrogate problem that gauges an LLM's aptitude to deduce an entity by posing a series of queries to the judge. 
- Through systematic evaluations, we analyze diverse LLMs and uncover noteworthy disparities in their performance on this particular task.

<div align="center">

| Model        |    #Turns (↓)   | Success (↑) |    #Yes     | Score (↑) |
|--------------|:------------------:|:---------:|:-------------:|:--------:|
| GPT-4-0613        | **16.9±0.2**       | **0.49±0.06** | 6.0±0.2    | **0.40±0.05** |
| GPT-3.5-turbo-0613      | 18.4±0.3            | 0.25±0.04  | 7.1±0.4    | 0.21±0.04 |
| Claude-2     | 17.6±0.3            | 0.29±0.05  | 4.5±0.3    | 0.25±0.04 |
| Claude-1     | 18.7±0.1            | 0.15±0.02  | 4.3±0.2    | 0.13±0.02 |
| Vicuna 13B (v1.3)  | 18.7±0.2            | 0.20±0.03  | 5.2±0.3    | 0.17±0.02 |
| Vicuna 7B (v1.3)   | 19.1±0.4            | 0.11±0.06  | 5.7±0.6    | 0.10±0.05 |

</div>


## Install dependencies
```bash
pip install -r requirements.txt
```

## Specify your OpenAI credential (API key)
```bash
export OPENAI_API_KEY="sk-XXXX"
```
## Run the game in commandline

Example usage:
```bash
# GPT3.5 play against GPT3.5 on Things.
python GPT_Q20.py --input data/things/list_of_things_eval.txt -g gpt-3.5-turbo
# GPT4 play against GPT3.5 on Celebs.
python GPT_Q20_celebrity.py --input data/celebrities/list_of_people_eval.txt -g gpt-4
# Vicuna 7b play against GPT3.5 on Things with 5 repetitions.
python GPT_Q20.py --input data/things/list_of_things_eval.txt -g lmsys/vicuna-7b-v1.3 --openai-api False -s hf --num-sessions 5
```
The execution of the above command will create of an output folder named `./data/<model_name>`. This folder contains the game play sessions for all the tested entities. 

### Command-line Arguments:

*Required:*

- `--input`: Specifies the input data to the script.

- `-g, --guesser_model`: Specify the model for guessing. Examples: gpt-4, gpt-3.5, gpt-3.5-turbo, claude-1, claude-2, lmsys/vicuna-7b-v1.3, lmsys/vicuna-13b-v1.3, meta-llama/Llama-2-13b-chat-hf ...

Please note that when using models from the huggingface hub or from a local path, such as lmsys/vicuna-7b-v1.3 or /mnt/ckpts/checkpoint_400 (a local path), you need to set `--openai-api` to `False` in order to load the model correctly. Alternatively, you can set up an openAI API server from the checkpoint as per the instructions provided in the [FastChat repository](https://github.com/lm-sys/FastChat/blob/main/docs/openai_api.md). In this scenario, `--openai-api` should remain `True`.

*Optional:*

- `--answerer_model`: Specify the model for answering questions. Default to GPT-3.5-turbo

- `--suffix`: Optional suffix to modify output or data.

- `--user`: User name for user mode

- `--turns`: Set the maximum number of turns for the game.

- `--temp`: Set the temperature for model sampling.

- `--num-sessions`: Set the number of sessions or iterations.

- `--openai-api`: Whether or not to use OpenAI API server for the guesser model. Default to `True`.


## Batch evaluation
Specify the model as `<your_model>`. If opting for a model path, set `--openai-api` False.
```bash
for rep in 1 2 3 4 5; do
    python script/eval_result.py --dir ./data/<your_model>_rep${rep}
done
```
Then running the following code to compare and summarize all the results across models in the entire folder:
```bash
python script/breakdown_stats.py --dir ./data
```

## Setting a demo server
Coming soon.

## Citation
Please consider citing our work if it is helpful to your research.
```
@article{zhang2023entity,
  title={The Entity-Deduction Arena: A playground for probing the conversational reasoning and planning capabilities of LLMs},
  author={Zhang, Yizhe and Lu, Jiarui and Jaitly, Navdeep},
  journal={arXiv preprint arXiv:2310.01468},
  year={2023}
}
```

## Poster
<p align = "center">
<img src="imgs/poster.png" width="100%" alt="" align=center />
</p>
<p align = "center">
Poster for the entity-deduction arena
</p>
