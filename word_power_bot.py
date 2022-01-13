from functools import cache
from os import makedirs
from os.path import exists
from random import choice
from re import IGNORECASE, compile, sub
from typing import Optional
from unicodedata import normalize
from urllib.parse import quote

from bs4 import BeautifulSoup
from discord import AudioSource, FFmpegPCMAudio, Message, VoiceClient, VoiceState
from discord.ext.commands import Bot, CommandError, CommandNotFound, Context, DefaultHelpCommand
from requests import Response, get

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

def get_chrome(ahdictionary_url: str) -> Response:
	# anti-anti-bot User-Agent
	headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36'}
	response = get(ahdictionary_url, headers=headers)
	return response

def download_file(path: str, url: str):
	if not exists(path):
		with open(path, 'wb') as file:
			response = get_chrome(url)
			file.write(response.content)
		print(f"downloaded {path} from {url}")

class Word:
	ERROR_AUDIO_PATH = 'wavs/$error.wav'

	@staticmethod
	@cache
	def make_word(word_entry: str):
		return Word(word_entry)

	def __init__(self, word_entry: str):
		self.word_entry = word_entry
		self.spellings = Word.extract_spellings(self.word_entry)
		search_results = Word.get_search_results(self.spellings[0])
		definition = Word.get_definition(search_results)
		for spelling in self.spellings:
			definition = sub(compile(spelling, IGNORECASE), '###', definition)
		self.definition = definition
		self.audio_path, self.audio_url = Word.get_pronunciation(search_results)

	def __repr__(self):
		return f"Word({self.word_entry!r})"

	@staticmethod
	def extract_spellings(word_entry: str) -> list[str]:
		if word_entry[-1] == '*':
			word_entry = word_entry[:-2]
		if word_entry[-1] == ')':
			word_entry = word_entry[:word_entry.find(' (')]
		return word_entry.split('/')

	@staticmethod
	def get_search_results(query: str) -> BeautifulSoup:
		search_url = f"https://www.ahdictionary.com/word/search.html?q={quote(query)}"
		search_response = get_chrome(search_url)
		search_results = BeautifulSoup(search_response.content, 'html.parser').find(id='results')
		return search_results

	@staticmethod
	def get_definition(search_results: BeautifulSoup) -> str:
		return '\n'.join(ds.text.strip() for ds in search_results(class_=('ds-single', 'ds-list')))

	@staticmethod
	def get_pronunciation(search_results: BeautifulSoup) -> tuple[str, str]:
		audio_anchor = search_results.find('a', target='_blank')
		if audio_anchor and audio_anchor['href'].endswith('.wav'):
			wav_path = audio_anchor['href']
			wav_path = wav_path[wav_path.rindex('/') - 4:]
			wav_url = f"https://ahdictionary.com/application/resources/{wav_path}"
		else:
			wav_path = Word.ERROR_AUDIO_PATH
			wav_url = 'https://ahdictionary.com/application/resources/wavs/E0202600.wav'
		return wav_path, wav_url

	async def define(self, msg: Message):
		await msg.channel.send(self.definition or 'no definition found')

	async def pronounce(self, msg: Message):
		global voice_client
		download_file(self.audio_path, self.audio_url)
		print(f"pronouncing {self.word_entry!r} (stored locally at {self.audio_path})")
		voice_state: VoiceState = msg.author.voice
		if voice_state:
			if not voice_client:
				voice_client = await voice_state.channel.connect()
				await msg.guild.change_voice_state(channel=voice_state.channel, self_deaf=True)
			if voice_client.channel != voice_state.channel:
				await voice_client.move_to(voice_state.channel)
				await msg.guild.change_voice_state(channel=voice_state.channel, self_deaf=True)
			if not voice_client.is_playing():  # and voice_client.is_connected() ?
				audio_source: AudioSource = FFmpegPCMAudio(self.audio_path, before_options='-channel_layout mono')
				voice_client.play(audio_source)
		else:
			await msg.channel.send(f"{msg.author} is not in a voice channel, cannot `pronounce`")
		if self.audio_path == Word.ERROR_AUDIO_PATH:
			await msg.channel.send('no pronunciation found')
			await self.define(msg)

voice_client: Optional[VoiceClient] = None

dp = []
def levenshtein_distance(s, t):
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
	word = ' '.join(word)
	await (Word.make_word(word)
	       if word else hidden_word
	       ).pronounce(ctx.message)

@bot.command(aliases=('d', 'definition'))
async def define(ctx: Context, *word: str):
	word = ' '.join(word)
	await (Word.make_word(word)
	       if word else hidden_word
	       ).define(ctx.message)

@bot.command(aliases=('e', 'edit-distance', 'ed', 'levenshtein-distance', 'ld', 'lev', 'l', 'distance', 'dist', 'difference', 'diff'))
async def edit(ctx: Context, *word: str):
	word = ' '.join(word)
	await ctx.send(f"{min(levenshtein_distance(word, spelling) for spelling in hidden_word.spellings)}")

@bot.command(aliases=('n', 'new-word', 'nw'))
async def new(ctx: Context):
	await ctx.send(hidden_word_entry)
	randomize_hidden()
	await hidden_word.pronounce(ctx.message)

@bot.command(aliases=('s', 'give-up', 'g'))
async def show(ctx: Context):
	await ctx.send(hidden_word_entry)

@bot.event
async def on_message(msg: Message):
	if msg.author == bot.user:
		return
	msg.content = translate_accents(msg.content)
	if msg.content in hidden_word.spellings:
		await msg.add_reaction('\N{white heavy check mark}')
		randomize_hidden()
		await hidden_word.pronounce(msg)
	else:
		await bot.process_commands(msg)

# noinspection PyUnusedLocal
@bot.event
async def on_command_error(ctx: Context, error: CommandError):
	if not isinstance(error, CommandNotFound):
		raise error

if __name__ == '__main__':
	if not exists('wavs'):
		makedirs('wavs')
	randomize_hidden()
	bot.run(os.environ['BOT_TOKEN'])
