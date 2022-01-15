from functools import cache
from os import makedirs
from os.path import dirname, exists
from re import IGNORECASE, compile as re_compile, sub
from typing import Optional
from urllib.parse import quote

from bs4 import BeautifulSoup
from requests import Response, get

"""
Word entries obey the following grammar:

SPELLING := sequence of non-newline and non / ( ) * characters
SPELLINGS := SPELLING, or SPELLINGS/SPELLING
PARENTHESIZED := SPELLINGS (SPELLING)
VOCABULARY := SPELLINGS *, or PARENTHESIZED *
WORD ENTRY := SPELLINGS, or PARENTHESIZED, or VOCABULARY

see word_power_words.txt for examples
"""


def get_as_chrome(url: str) -> Response:
	"""GETs a url using a Chrome / Windows 10 User-Agent"""
	# for https://ahdictionary.com/ the default User-Agent 'python-requests/version' no longer works
	# after it stopped working, I implemented download caching to reduce load
	headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36'}
	return get(url, headers=headers)

def cached_download(path: str, url: str):
	"""Downloads `url` to `path` if and only if `path` does not exist."""
	if not exists(path):
		with open(path, 'wb') as file:
			response = get_as_chrome(url)
			file.write(response.content)
		print(f"downloaded {path} from {url}")

class Word:
	"""Represents a word's definition and pronunciation as returned by querying https://ahdictionary.com/"""

	@staticmethod
	@cache
	def make_word(word_entry: str):
		return Word(word_entry)

	def __init__(self, word_entry: str):

		self.word_entry: str = word_entry
		"""The word entry represented by this Word"""
		self.spellings: tuple[str, ...] = Word._extract_spellings(self.word_entry)
		"""The accepted spellings of this word."""

		search_results = Word._query_search_results(self.spellings[0])

		definition = Word._extract_definition(search_results)
		for spelling in self.spellings:
			definition = sub(re_compile(spelling, IGNORECASE), '###', definition)
		self.definition: str = definition
		"""Definition of the word, where instances of the word in the definition are replaced by '###'."""

		audio_path, audio_url = Word._extract_pronunciation(search_results)
		self._audio_path: str = audio_path
		"""The path to the cached pronunciation audio file."""
		self._audio_url: str = audio_url
		"""The url to the pronunciation audio file"""

	def __repr__(self) -> str:
		return f"Word({self.word_entry!r})"

	@staticmethod
	def _extract_spellings(word_entry: str) -> tuple[str, ...]:
		"""Extracts spellings from a word entry (refer to the word entry grammar towards the top of this file)."""
		if word_entry[-1] == '*':
			word_entry = word_entry[:-2]
		if word_entry[-1] == ')':
			word_entry = word_entry[:word_entry.find(' (')]
		return tuple(word_entry.split('/'))

	@staticmethod
	def _query_search_results(query: str) -> BeautifulSoup:
		"""Queries https://www.ahdictionary.com/ and returns the results div"""
		url = f"https://www.ahdictionary.com/word/search.html?q={quote(query)}"
		response = get_as_chrome(url)
		return BeautifulSoup(response.content, 'html.parser').find(id='results')

	@staticmethod
	def _extract_definition(search_results: BeautifulSoup) -> str:
		"""Parses the search results div for the definition."""
		return '\n'.join(ds.text.strip() for ds in search_results(class_=('ds-single', 'ds-list')))

	@staticmethod
	def _extract_pronunciation(search_results: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
		"""Parses the search results div for a link to a pronunciation audio file."""
		# finds the first <a> with attribute target="_blank" since these are typically audios
		audio_anchor = search_results.find('a', target='_blank')
		if audio_anchor and audio_anchor.has_attr('href'):
			href = audio_anchor['href']
			audio_path = f"cache{href}"
			audio_url = f"https://ahdictionary.com{href}"
		else:
			# some dictionary entries don't have pronunciations
			audio_path = None
			audio_url = None
		return audio_path, audio_url

	@property
	def has_pronunciation_path(self) -> bool:
		return self._audio_path is not None

	@property
	def pronunciation_path(self) -> Optional[str]:
		"""Returns a path to the pronunciation file of this word, first ensuring that it is downloaded."""
		if not exists(self._audio_path):
			makedirs(dirname(self._audio_path), exist_ok=True)
			with open(self._audio_path, 'wb') as file:
				response = get_as_chrome(self._audio_path)
				file.write(response.content)
		return self._audio_path
