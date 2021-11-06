from random import choice
from requests import get
from bs4 import BeautifulSoup
from urllib.parse import quote
from functools import lru_cache
from re import compile, IGNORECASE, sub
from discord import Client, Member, FFmpegPCMAudio

def convert_accents(s):
	for typed, accented in ('a\\', 'à'), ('a/', 'á'), ('a^', 'â'), ('a:', 'ä'), \
	                       ('c,', 'ç'), \
	                       ('e\\', 'è'), ('e/', 'é'), ('e^', 'ê'), ('e:', 'ë'), \
	                       ('i^', 'î'), \
	                       ('n~', 'ñ'), \
	                       ('o/', 'ó'), ('o^', 'ô'), ('o:', 'ö'), \
	                       ('u/', 'ú'), ('u^', 'û'):
		s = s.replace(typed, accented)
	return s

# connect to the voice channel of the user who mentioned the bot
async def summon(msg):
	global voice_channel, voice_client, hidden_word
	if not hidden_word:
		randomize_word()
	if isinstance(msg.author, Member):
		if voice_state := msg.author.voice:
			if voice_channel != voice_state.channel:
				voice_channel = voice_state.channel
				if voice_client:
					await voice_client.disconnect()
				voice_client = await voice_channel.connect()
				await msg.guild.change_voice_state(channel=voice_channel, self_deaf=True)

# l
def get_dictionary_url(word):
	return f"https://www.ahdictionary.com/word/search.html?q={quote(word)}"

@lru_cache(8)
def get_soup(word):
	return BeautifulSoup(get(get_dictionary_url(word)).text, 'html.parser').find(id='results')

# convert a word to an audio URL
@lru_cache(8)
def get_audio_url(word):
	name = get_soup(word).find(target='_blank')
	if not name or not (name := name['href']).endswith('.wav'):
		name = '/application/resources/wavs/E0202600.wav'  # error
	return f"https://ahdictionary.com{name}"

# p
def pronounce_word(word):
	if voice_client and voice_client.is_connected():
		url = get_audio_url(word)
		voice_client.play(FFmpegPCMAudio(url, options='-ar 48000'))

dp = [list(range(22))]
def levenshtein_distance(s, t):
	n, m = len(s), len(t)
	while len(dp) <= n:
		dp.append([len(dp)]*22)
	for i in range(1, n + 1):
		for j in range(1, m + 1):
			dp[i][j] = min((
				dp[i - 1][j] + 1,
				dp[i][j - 1] + 1,
				dp[i - 1][j - 1] + (s[i - 1] != t[j - 1])
			))
	return dp[n][m]

# e
def min_edits(guess):
	return min(levenshtein_distance(guess, spelling) for spelling in spellings)

# s
@lru_cache(8)
def get_definition(word):
	soup = get_soup(word)
	if div := soup.find(align='right'):
		div.decompose()
	definition = '\n'.join(ds.text.strip() for ds in soup(class_=('ds-list', 'ds-single')))
	for spelling in spellings:
		definition = sub(compile(spelling, IGNORECASE), '###', definition)
	return definition

# n
hidden_word = ''
spellings = []
# from random import shuffle
# def reset():
#	global lines
#	with open(r'C:\Users\panda\programming\discord\bots\word_power_words.txt',
#          	encoding='utf8') as file:
#		lines = file.read().splitlines()
#	shuffle(lines)
# reset()
with open(r'C:\Users\panda\programming\discord\bots\word_power_words.txt',
          encoding='utf8') as file:
	lines = file.read().splitlines()

with open(r'C:\Users\panda\programming\discord\bots\word_power_banned.txt', encoding='utf8') as f:
	bans = set(f.read().splitlines())
	lines = [line for line in lines if line not in bans]
# each of the 1500 words has an equal probability.
# within each word, each spelling has an equal probability.
# from random import shuffle
# shuffle(lines)
# it = iter(lines)
def randomize_word():
	global hidden_word, spellings
	hidden_word = spellings = choice(lines)  # lines.pop() #choice(lines)
	#	hidden_word = spellings = next(it)
	if spellings[-1] == '*':
		spellings = spellings[:-2]
	if spellings[-1] == ')':
		spellings = spellings[:spellings.find(' (')]
	spellings = spellings.split('/')

voice_channel = voice_client = None
client = Client()

from time import sleep

@client.event
async def on_message(msg):
	global lines
	#	sleep(5)
	#	msg.content = 'n'
	if msg.author == client.user:
		return
	msg.content = convert_accents(msg.content)
	# correct answer
	if msg.content in spellings:
		await msg.add_reaction('\N{WHITE HEAVY CHECK MARK}')
		await msg.channel.send(hidden_word)
		randomize_word()
		pronounce_word(spellings[0])
		await msg.channel.send(get_definition(spellings[0]))
	# pronounce
	elif msg.content == 'p':
		await summon(msg)
		pronounce_word(spellings[0])
	elif msg.content.startswith('p '):
		await summon(msg)
		pronounce_word(msg.content[msg.content.find(' ') + 1:])
	# query edit distance
	elif msg.content.endswith('.'):
		await summon(msg)
		e = min_edits(msg.content[msg.content.find(' ') + 1:-1])
		await msg.channel.send(e)
		await msg.add_reaction(f"{e%12}️⃣" if e < 10 else '\N{CROSS MARK}')
	# search definition
	elif msg.content == 's':
		await summon(msg)
		await msg.channel.send(get_definition(spellings[0]))
	elif msg.content.startswith('s '):
		await summon(msg)
		await msg.channel.send(get_definition(msg.content[msg.content.find(' ') + 1:]))
	# new word
	elif msg.content == 'n':
		await msg.channel.send(hidden_word)
		randomize_word()
		await summon(msg)
		pronounce_word(spellings[0])
		await msg.channel.send(get_definition(spellings[0]))
	# give up
	elif msg.content == 'G' or msg.content == 'g':
		await summon(msg)
		await msg.channel.send(hidden_word)
	# get link
	elif msg.content == 'l':
		await summon(msg)
		await msg.channel.send(get_dictionary_url(spellings[0]))
	elif msg.content.startswith('l '):
		await summon(msg)
		await msg.channel.send(get_dictionary_url(msg.content[msg.content.find(' ') + 1:]))
	elif msg.content.startswith('ban'):
		ban = msg.content[msg.content.find(' ') + 1:]
		if ban in lines:
			lines.remove(ban)
			with open(r'C:\Users\panda\programming\discord\bots\word_power_banned.txt', 'a', -1, 'utf8', newline='\n') as f:
				f.write(ban)
				f.write('\n')
	elif msg.content.startswith('unban'):
		ban = msg.content[msg.content.find(' ') + 1:]
		with open(r'C:\Users\panda\programming\discord\bots\word_power_banned.txt', 'r', -1, 'utf8', newline='\n') as f:
			bans = [x for x in f.read().splitlines() if x and x != ban]
		with open(r'C:\Users\panda\programming\discord\bots\word_power_banned.txt', 'w', -1, 'utf8', newline='\n') as f:
			f.write('\n'.join(bans))
			f.write('\n')
		with open(r'C:\Users\panda\programming\discord\bots\word_power_words.txt',
		          encoding='utf8') as file:
			lines = file.read().splitlines()
		with open(r'C:\Users\panda\programming\discord\bots\word_power_banned.txt', encoding='utf8') as f:
			bans = set(f.read().splitlines())
			lines = [line for line in lines if line not in bans]
	elif msg.content == 'b':
		ban = hidden_word
		if ban in lines:
			lines.remove(ban)
			with open(r'C:\Users\panda\programming\discord\bots\word_power_banned.txt', 'a', -1, 'utf8', newline='\n') as f:
				f.write(ban)
				f.write('\n')
		await msg.channel.send(hidden_word)
		randomize_word()
		await summon(msg)
		pronounce_word(spellings[0])
		await msg.channel.send(get_definition(spellings[0]))
	#	elif msg.content == 'reset':
	#		reset()
	elif msg.content == 'r':
		await msg.channel.send(choice(lines))
	elif msg.content == 'ra':
		await msg.channel.send(choice(lines))

client.run(os.environ['BOT_TOKEN'])
