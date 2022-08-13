import word_power_bot
import unittest
import string

class TestAccentTranslation(unittest.TestCase):
	accented_letter_cases = {
		'a\\': 'à', 'a/': 'á', 'a^': 'â', 'a:': 'ä',
		'c,' : 'ç',
		'e\\': 'è', 'e/': 'é', 'e^': 'ê', 'e:': 'ë',
		'i/' : 'í', 'i^' : 'î',
		'n~' : 'ñ',
		'o/' : 'ó', 'o^': 'ô', 'o:': 'ö',
		'u/' : 'ú', 'u^': 'û',
	}
	accented_word_cases = {
		'Alenc,on'          : 'Alençon',
		'belle e/poque'     : 'belle époque',
		'fla^neur'          : 'flâneur',
		'Neufcha^tel'       : 'Neufchâtel',
		'risque/'           : 'risqué',
		'Ade/lie penguin'   : 'Adélie penguin',
		'ancien re/gime'    : 'ancien régime',
		'applique/'         : 'appliqué',
		'Asuncio/n'         : 'Asunción',
		'attache/ case'     : 'attaché case',
		'Averroe:s'         : 'Averroës',
		'Averrhoe:s'        : 'Averrhoës',
		'be^tise'           : 'bêtise',
		'boi^te'            : 'boîte',
		'bonbonnie\\re'     : 'bonbonnière',
		'boucle/'           : 'bouclé',
		'cafe/ noir'        : 'café noir',
		'canape/'           : 'canapé',
		'cha^teau'          : 'château',
		'coup de the/a^tre' : 'coup de théâtre',
		'cre\\che'          : 'crèche',
		'de/collete/'       : 'décolleté',
		'de/ja\\ vu'        : 'déjà vu',
		'de/marche'         : 'démarche',
		'divorce/e'         : 'divorcée',
		'engage/'           : 'engagé',
		'e/tage\\re'        : 'étagère',
		'Faberge/'          : 'Fabergé',
		'fiance/'           : 'fiancé',
		'flambe/ed'         : 'flambéed',
		'Gala/pagos Islands': 'Galápagos Islands',
		'lame/'             : 'lamé',
		'ma^che'            : 'mâche',
		'matelasse/'        : 'matelassé',
		'Mo:bius strip'     : 'Möbius strip',
		'moire/ effect'     : 'moiré effect',
		'pin~ata'           : 'piñata',
		'plie/'             : 'plié',
		'Provenc,al'        : 'Provençal',
		're/chauffe/'       : 'réchauffé',
		're/moulade'        : 'rémoulade',
		're/sume/'          : 'résumé',
		'resume/'           : 'resumé',
		'vis-a\\-vis'       : 'vis-à-vis',
		'voila\\'           : 'voilà',
	}

	def test_accented_letters(self):
		for untranslated, expected_translation in TestAccentTranslation.accented_letter_cases.items():
			with self.subTest(expected_translation):
				self.assertEqual(word_power_bot.translate_accents(untranslated), expected_translation)

	def test_accented_words(self):
		for untranslated, expected_translation in TestAccentTranslation.accented_word_cases.items():
			with self.subTest(expected_translation):
				self.assertEqual(word_power_bot.translate_accents(untranslated), expected_translation)

	def test_unaccented_chars(self):
		for letter in string.ascii_letters:
			with self.subTest(letter):
				self.assertEqual(word_power_bot.translate_accents(letter), letter)

class TestEditDistance(unittest.TestCase):
	cases = [
		('123', '12', 1),
		('kitten', 'smitten', 2),
		('kitten', 'mitten', 1),
		('kitten', 'kitty', 2),
		('kitten', 'fitting', 3),
		('kitten', 'written', 2),
		('kitten', 'sitten', 1),
		('sitten', 'sittin', 1),
		('sittin', 'sitting', 1),
		('kitten', 'sitting', 3),
		('Saturday', 'Sunday', 3),
		('rosettacode', 'raisethysword', 8),
		('geek', 'gesek', 1),
		('cat', 'cut', 1),
		('sunday', 'saturday', 3),
		('sea','ate',3),
		('horse','ros',3)
	]
	cases=cases[-1:]

	def test(self):
		for s, t, dist in TestEditDistance.cases:
			with self.subTest(s=s, t=t,dist=dist):
				self.assertEqual(word_power_bot.levenshtein_distance(s, t), dist)
			with self.subTest(s=t, t=s,dist=dist):
				self.assertEqual(word_power_bot.levenshtein_distance(t, s), dist)

if __name__ == '__main__':
	unittest.main()
