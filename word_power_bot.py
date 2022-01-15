from random import choice
from typing import Optional
from unicodedata import normalize

from discord import AudioSource, FFmpegPCMAudio, Message, VoiceClient, VoiceState
from discord.ext.commands import Bot, CommandError, CommandNotFound, Context, DefaultHelpCommand

from ahdictionary import Word

ACCENT_TRANSLATION_TABLE: dict = str.maketrans({
	'\\': '\N{combining grave accent}',  # àè
	'/' : '\N{combining acute accent}',  # áéóú
	'^' : '\N{combining circumflex accent}',  # âêîôû
	'~' : '\N{combining tilde}',  # ñ
	':' : '\N{combining diaeresis}',  # äëö
	',' : '\N{combining cedilla}',  # ç
})

def translate_accents(untranslated: str) -> str:
	return normalize('NFC', untranslated.translate(ACCENT_TRANSLATION_TABLE))

async def define_word(msg: Message, word: Word):
	"""Sends the definition, if one was found."""
	await msg.channel.send(word.definition or 'no definition found')

async def pronounce_word(msg: Message, word: Word):
	"""Attempts to join the message user's current voice channel and play the pronunciation."""
	global voice_client
	if word.has_pronunciation_path:
		print(f"pronouncing {word.word_entry!r}")
		voice_state: VoiceState = msg.author.voice
		if voice_state:
			if not voice_client:
				voice_client = await voice_state.channel.connect()
				await msg.guild.change_voice_state(channel=voice_state.channel, self_deaf=True)
			if voice_client.channel != voice_state.channel:
				await voice_client.move_to(voice_state.channel)
				await msg.guild.change_voice_state(channel=voice_state.channel, self_deaf=True)
			if not voice_client.is_playing():  # and voice_client.is_connected() ?
				audio_source: AudioSource = FFmpegPCMAudio(word.pronunciation_path, before_options='-channel_layout mono')
				voice_client.play(audio_source)
		else:
			await msg.channel.send(f"{msg.author} is not in a voice channel, cannot pronounce word")
	else:
		await msg.channel.send('no pronunciation found')
		await define_word(msg, word)

voice_client: Optional[VoiceClient] = None

dp = []
def levenshtein_distance(s: str, t: str) -> int:
	"""Computes the Levenshtein distance between two strings."""
	global dp
	# https://www.baeldung.com/cs/levenshtein-distance-computation
	print(f"calculating levenshtein distance between {s!r} and {t!r}")
	if len(s) < len(t):
		s, t = t, s
	n, m = len(s), len(t)
	if len(dp) < m + 1:
		dp.extend(range(m + 1 - len(dp)))
	dp[:m + 1] = range(m + 1)
	for i in range(n):
		prev_above = dp[0]
		dp[0] = i + 1
		for j in range(m):
			prev_diag = prev_above
			prev_above = dp[j + 1]
			dp[j + 1] = min(prev_above + 1, dp[j] + 1, prev_diag + (s[i] != t[j]))
	return dp[m]

with open(r'word_power_words.txt', encoding='utf8') as file:
	word_entries = file.read().splitlines()

hidden_word_entry: str
hidden_word: Word
def randomize_hidden():
	global hidden_word_entry, hidden_word
	hidden_word_entry = choice(word_entries)
	hidden_word = Word.make_word(hidden_word_entry)
	print(f"randomized to {hidden_word_entry!r}")

bot = Bot(
	command_prefix='',
	help_command=DefaultHelpCommand(
		no_category='commands',
		sort_commands=False
	),
	description='bot for practicing for spelling & vocabulary uil',
	case_insensitive=True,
)

@bot.command(aliases=('p', 'pronunciation'))
async def pronounce(ctx: Context, *word: str):
	"""Plays the pronunciation of the hidden word, if one was found."""
	word = ' '.join(word)
	await pronounce_word(ctx.message, Word.make_word(word) if word else hidden_word)

@bot.command(aliases=('d', 'definition'))
async def define(ctx: Context, *word: str):
	"""Sends the definition of the hidden word, if one was found."""
	word = ' '.join(word)
	await define_word(ctx.message, Word.make_word(word) if word else hidden_word)

@bot.command(aliases=('e', 'edit-distance', 'ed', 'levenshtein-distance', 'ld', 'lev', 'l', 'distance', 'dist', 'difference', 'diff'))
async def edit(ctx: Context, *word: str):
	"""Sends the minimum possible Levenshtein distance between the guess and a spelling of the hidden word."""
	word = ' '.join(word)
	await ctx.send(f"{min(levenshtein_distance(word, spelling) for spelling in hidden_word.spellings)}")

@bot.command(aliases=('n', 'new-word', 'nw'))
async def new(ctx: Context):
	"""Reveals the old word and sets the new word."""
	await ctx.send(hidden_word_entry)
	randomize_hidden()
	await pronounce_word(ctx.message, hidden_word)

@bot.command(aliases=('s', 'give-up', 'g'))
async def show(ctx: Context):
	"""Reveals the hidden word."""
	await ctx.send(hidden_word_entry)

@bot.event
async def on_message(msg: Message):
	"""If the message matches the hidden word, reacts with a check mark emoji and sets the next word.
	Otherwise, processes the message as if it were a command.
	"""
	if msg.author == bot.user:
		return
	msg.content = translate_accents(msg.content)
	if msg.content in hidden_word.spellings:
		await msg.add_reaction('\N{white heavy check mark}')
		randomize_hidden()
		await pronounce_word(msg, hidden_word)
	else:
		await bot.process_commands(msg)

# noinspection PyUnusedLocal
@bot.event
async def on_command_error(ctx: Context, error: CommandError):
	"""Ignores CommandNotFound errors because the bot command prefix is empty."""
	if not isinstance(error, CommandNotFound):
		raise error

if __name__ == '__main__':
	randomize_hidden()
	from config import bot_token
	bot.run(bot_token)
