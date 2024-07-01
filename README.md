# Discord Code Review Bot

This Discord bot provides automated code reviews and interactive Q&A sessions for programming-related queries. It leverages the power of ChatGPT to analyze code, provide feedback, and answer follow-up questions.

## Features

- Automated code reviews for multiple programming languages
- Interactive Q&A sessions after each code review
- Support for code submission via text or file attachment
- Timeout functionality to manage conversation length
- Error handling and logging for robustness

## Prerequisites

Before you begin, ensure you have met the following requirements:

- Python 3.8 or higher
- A Discord account and a registered Discord application/bot
- An OpenAI API key for ChatGPT access

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/discord-code-review-bot.git
   cd discord-code-review-bot
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `config.py` file in the root directory with the following content:
   ```python
   DISCORD_TOKEN = 'your_discord_bot_token'
   PREFIX = '!'  # or any prefix you prefer
   CHATGPT_API_TOKEN = 'your_openai_api_key'
   CODE_REVIEW_PROMPT_PATH = 'path/to/your/code_review_prompts.json'
   ```

4. Create a `code_review_prompts.json` file with your desired prompts for the code review system and ChatGPT.

## Usage

1. Start the bot:
   ```
   python bot.py
   ```

2. In a Discord server where the bot is invited, use the following command to start a code review:
   ```
   !review
   ```

3. Follow the bot's prompts to provide:
   - Problem description
   - Programming language
   - Code (either pasted or as a file attachment)

4. After the code review, you can ask follow-up questions about the review.

5. The conversation will automatically end after 5 minutes of inactivity, or you can type 'finish' to end it manually.

## Commands

- `!review`: Start a new code review session
- `!shutdown`: Shut down the bot (owner-only command)

## Contributing

Contributions to the Discord Code Review Bot are welcome. Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Discord.py](https://discordpy.readthedocs.io/) for the Discord API wrapper
- [OpenAI](https://openai.com/) for the ChatGPT API

## Support

If you encounter any problems or have any questions, please open an issue in the GitHub repository.
