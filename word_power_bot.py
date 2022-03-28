from collections import defaultdict
from io import StringIO
from json import dumps
from os import environ
from random import choice, choices
from typing import Optional
from unicodedata import normalize

from discord import AudioSource, FFmpegPCMAudio, File, Intents, Message, TextChannel, User, VoiceClient, VoiceState
from discord.ext.commands import Bot, CommandError, CommandNotFound, Context, DefaultHelpCommand
from requests import JSONDecodeError, get

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
	"""Converts symbols for easy accent input."""
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

# data_channel_id = environ['DATA_CHANNEL_ID']
data_channel: TextChannel
data: dict
word_entries: list[str]
weights: defaultdict[str, defaultdict[str, float]]
aggression_value: float

async def load_data(channel_id: int = int(environ['DATA_CHANNEL_ID'])):
	global word_entries, weights, aggression_value
	channel: TextChannel = bot.get_channel(channel_id)
	try:
		last_message: Message = await channel.fetch_message(channel.last_message_id)
	except:
		await channel.send('could not load last message (this might happen if the last message got deleted)')
		raise
	if len(last_message.attachments) < 1:
		await channel.send('last message has no attachments')
		return
	data_url: str = last_message.attachments[0]
	print(f"data url: {data_url}")
	try:
		data = get(data_url).json()
	except JSONDecodeError:
		await channel.send('bad data (invalid json)')
		raise

	if 'words' not in data:
		await channel.send('bad data (missing words)')
		return
	if not isinstance(data['words'], list) or not all(isinstance(word, str) for word in data['words']):
		await channel.send('bad data (words is not an array of strings)')
		return
	word_entries = data['words']

	if 'weights' not in data:
		await channel.send('bad data (missing weights)')
		return
	print('json weights could be misformatted (i dont wanna validate)')
	weights = defaultdict(lambda: defaultdict(lambda: 0.5))
	for username, w in data['weights'].items():
		weights[username] = defaultdict(lambda: 0.5, w)

	if 'aggression_value' not in data:
		await channel.send('bad data (missing aggression value)')
		return
	if not isinstance(data['aggression_value'], (int, float)):
		await channel.send('bad data (non-numeric aggression value)')
		return
	if data['aggression_value'] <= 1.0:
		await channel.send('bad data (aggression_value must be >1)')
		return
	aggression_value = float(data['aggression_value'])

async def store_data(channel_id: int = int(environ['DATA_CHANNEL_ID'])):
	channel: TextChannel = bot.get_channel(channel_id)
	await channel.send(file=File(
		StringIO(dumps(
			{'aggression_value': aggression_value, 'weights': weights, 'words': word_entries},
			ensure_ascii=True, indent='\t'
		)), filename='data.json'
	))

hidden_word_entry: str
hidden_word: Word
async def randomize_hidden():
	global hidden_word_entry, hidden_word
	if voice_client is None:
		hidden_word_entry = choice(word_entries)
	else:
		voice_channel_user_ids: list[int] = [user_id for user_id in voice_client.channel.voice_states.keys() if user_id != bot.user.id]
		random_user: User = bot.get_user(choice(voice_channel_user_ids))
		if random_user:
			user_weights: defaultdict[str, float] = weights[str(random_user)]
			hidden_word_entry = choices(
				word_entries,
				[user_weights[word] for word in word_entries]
			)[0]
		else:
			hidden_word_entry = choice(word_entries)

	hidden_word = Word.make_word(hidden_word_entry)
	print(f"randomized to {hidden_word_entry!r}")

intents: Intents = Intents.default()
# noinspection PyDunderSlots,PyUnresolvedReferences
intents.members = True
bot = Bot(
	command_prefix='',
	help_command=DefaultHelpCommand(
		no_category='commands',
		sort_commands=False
	),
	intents=intents,
	description="""
bot for practicing for spelling & vocabulary uil

To input accented characters, add a special symbol after the character you wish to accent.
For example, espan~ol becomes español
more examples of supported accent conversions:
\ àè
/ áéóú
^ âêîôû
~ ñ
: äëö
, ç
Alternatively, just type the accented character.
""",
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
async def edit(ctx: Context, *guess: str):
	"""Sends the minimum possible Levenshtein distance between the guess and a spelling of the hidden word."""
	guess = ' '.join(guess)
	await ctx.send(f"{min(levenshtein_distance(guess, spelling) for spelling in hidden_word.spellings)}")

@bot.command(aliases=('n', 'new-word', 'nw'))
async def new(ctx: Context):
	"""Reveals the old word and sets the new word."""
	await ctx.send(hidden_word_entry)
	await randomize_hidden()
	await pronounce_word(ctx.message, hidden_word)
	if hidden_word_entry[-1] == '*':
		await define_word(ctx.message, hidden_word)

@bot.command(aliases=('s', 'give-up', 'g'))
async def show(ctx: Context):
	"""Reveals the hidden word."""
	await ctx.send(f"||{hidden_word_entry}||")

@bot.event
async def on_ready():
	await load_data()
	await randomize_hidden()

@bot.event
async def on_message(msg: Message):
	"""
	Try to processes the message as a command. (todo make sure none of the words are also commands)
	If no command is found, interpret the message as a guess.
	"""
	if msg.author != bot.user:
		msg.content = translate_accents(msg.content)
		await bot.process_commands(msg)

@bot.event
async def on_command_error(ctx: Context, error: CommandError):
	"""Interpret CommandNotFound errors as guesses, ignore other types of errors"""
	if isinstance(error, CommandNotFound):
		msg: Message = ctx.message
		old_weight: float = weights[str(ctx.author)][hidden_word_entry]
		new_weight: float
		# move left and right along the curve 1/(1+aggression_value**x)
		if msg.content in hidden_word.spellings:
			await msg.add_reaction('\N{large green square}')
			new_weight = old_weight/(aggression_value - old_weight*(aggression_value - 1))
		else:
			await msg.add_reaction('\N{large red square}')
			new_weight = aggression_value*old_weight/(1 + old_weight*(aggression_value - 1))
		weights[str(ctx.author)][hidden_word_entry] = new_weight
		await ctx.send(f"{hidden_word_entry}\nweight change: {old_weight:.2f}->{new_weight:.2f}")
		await randomize_hidden()
		await pronounce_word(msg, hidden_word)
		if hidden_word_entry[-1] == '*':
			await define_word(ctx.message, hidden_word)
		await store_data()
	else:
		raise error

if __name__ == '__main__':
	# randomize_hidden()
	bot.run(environ['BOT_TOKEN'])
