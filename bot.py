import discord
from discord.ext import commands
from config import DISCORD_TOKEN, PREFIX, CHATGPT_API_TOKEN, CODE_REVIEW_PROMPT_PATH, MAX_LENGTH
import aiohttp
import asyncio
import json
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Load the code review prompt
try:
    with open(CODE_REVIEW_PROMPT_PATH, 'r') as file:
        prompts = json.load(file)['prompts']
except FileNotFoundError:
    logger.error(f"Prompt file not found: {CODE_REVIEW_PROMPT_PATH}")
    prompts = []
except json.JSONDecodeError:
    logger.error(f"Invalid JSON in prompt file: {CODE_REVIEW_PROMPT_PATH}")
    prompts = []


def sanitize_input(text):
    # Remove any non-printable characters except newlines
    text = ''.join(char for char in text if char.isprintable() or char == '\n')
    # Limit the length of the input
    return text[:MAX_LENGTH]


async def get_chatgpt_response(messages):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post('https://api.openai.com/v1/chat/completions',
                                    headers={
                                        'Authorization': f'Bearer {CHATGPT_API_TOKEN}',
                                        'Content-Type': 'application/json'
                                    },
                                    json={
                                        'model': 'gpt-4o',
                                        'messages': messages,
                                        'max_tokens': 4096
                                    }) as response:
                if response.status == 200:
                    json_response = await response.json()
                    return json_response['choices'][0]['message']['content']
                else:
                    error_content = await response.text()
                    logger.error(f"ChatGPT API error: {error_content}")
                    return f"Error: Unable to get response. Status code: {response.status}"
    except aiohttp.ClientError as e:
        error_message = f"Network error occurred: {str(e)}"
        logger.error(error_message)
        return error_message
    except Exception as e:
        error_message = f"Unexpected error occurred: {str(e)}"
        logger.error(error_message)
        return error_message


async def get_code_review(problem_description, programming_language, submitted_code):
    if not prompts:
        return "Error: Code review prompts are not available."

    messages = [
        {"role": "system", "content": prompts[0]['content']},
        {"role": "user", "content": prompts[1]['content'].format(
            problem_description=problem_description,
            programming_language=programming_language,
            submitted_code=submitted_code
        )}
    ]

    return await get_chatgpt_response(messages)


@bot.event
async def on_ready():
    print(f'Bot {bot.user} is connected to Discord!')
    print("The bot is present on the following servers:")
    for guild in bot.guilds:
        print(f"- {guild.name} (id: {guild.id})")


@bot.command()
@commands.is_owner()
async def shutdown(ctx):
    await ctx.send("Shutting down...")
    await bot.close()


@bot.command(help="Start a code review process")
async def review(ctx):
    try:
        thread = await ctx.message.create_thread(name=f"Code Review for {ctx.author.name}")
    except discord.HTTPException as e:
        await ctx.send(f"Failed to create thread: {str(e)}")
        return

    await thread.send(
        "I will be asking you for the necessary information one by one. Please provide the code problem description:")

    info = {'problem_description': '', 'programming_language': '', 'submitted_code': ''}
    current_field = 'problem_description'

    def check(m):
        return m.author == ctx.author and m.channel == thread

    while True:
        try:
            msg = await bot.wait_for('message', check=check, timeout=300.0)
        except asyncio.TimeoutError:
            await thread.send("No response received within 5 minutes. The code review request has been cancelled.")
            return

        if msg.content.lower() == 'done':
            break

        if current_field == 'problem_description':
            info['problem_description'] = sanitize_input(msg.content)
            current_field = 'programming_language'
            await thread.send("Great, now please provide the programming language.")
        elif current_field == 'programming_language':
            info['programming_language'] = sanitize_input(msg.content)
            current_field = 'submitted_code'
            await thread.send("Now, please paste your code.")
        elif current_field == 'submitted_code':
            if msg.attachments:
                for attachment in msg.attachments:
                    if attachment.filename.endswith(
                            ('.py', '.js', '.java', '.cpp', '.cs')):  # Add more extensions if needed
                        try:
                            code = await attachment.read()
                            info['submitted_code'] = sanitize_input(code.decode('utf-8'))
                            break
                        except discord.HTTPException as e:
                            await thread.send(f"Failed to read attachment: {str(e)}")
                            continue
                else:
                    await thread.send(
                        "No valid code file found in the attachments. Please upload a file with a supported extension or paste your code directly.")
                    continue
            else:
                info['submitted_code'] = sanitize_input(msg.content)
            await thread.send("Thank you for providing all the information. Type 'done' to start the code review.")

    await thread.send("Analyzing your code... This may take a moment.")
    try:
        review = await get_code_review(**info)
    except Exception as e:
        error_message = f"An error occurred during code review: {str(e)}"
        logger.error(error_message)
        await thread.send(error_message)
        return

    # Split the review into chunks of 2000 characters or less (Discord's message limit)
    chunks = [review[i:i + 2000] for i in range(0, len(review), 2000)]
    for chunk in chunks:
        try:
            await thread.send(chunk)
        except discord.HTTPException as e:
            await thread.send(f"Failed to send review: {str(e)}")

    await thread.send(
        "Code review complete. You can now ask additional questions about the review. Type 'finish' when you're done or wait for 5 minutes of inactivity.")

    # Set up for Q&A session
    conversation_history = [
        {"role": "system", "content": "You are a helpful assistant answering questions about a code review. You do not answer any irrelevan questions"},
        {"role": "user",
         "content": f"Here's the context:\nProblem description: {info['problem_description']}\nProgramming language: {info['programming_language']}\nCode review: {review}"},
        {"role": "assistant",
         "content": "I understand the context. I'm ready to answer any questions about the code review."}
    ]

    end_time = datetime.now() + timedelta(minutes=5)

    while datetime.now() < end_time:
        try:
            msg = await bot.wait_for('message', check=check, timeout=300.0)
        except asyncio.TimeoutError:
            await thread.send("No activity for 5 minutes. Ending the conversation.")
            return

        if msg.content.lower() == 'finish':
            await thread.send("Thank you for using the code review service. Conversation ended.")
            return

        conversation_history.append({"role": "user", "content": msg.content})

        response = await get_chatgpt_response(conversation_history)
        conversation_history.append({"role": "assistant", "content": response})

        # Split the response into chunks of 2000 characters or less
        chunks = [response[i:i + 2000] for i in range(0, len(response), 2000)]
        for chunk in chunks:
            try:
                await thread.send(chunk)
            except discord.HTTPException as e:
                await thread.send(f"Failed to send response: {str(e)}")

        # Reset the 5-minute timer
        end_time = datetime.now() + timedelta(minutes=5)

    await thread.send("5 minutes have passed without any questions. Ending the conversation.")


try:
    bot.run(DISCORD_TOKEN)
except discord.LoginFailure:
    logger.error("Failed to log in: Invalid token")
except Exception as e:
    logger.error(f"An error occurred while running the bot: {str(e)}")