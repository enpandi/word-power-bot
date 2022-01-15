# word power bot

A Discord bot to help users practice for [UIL Spelling and Vocabulary](https://www.uiltexas.org/academics/academic-contests/spelling-and-vocabulary),
although it could also be used for other similar purposes.

## overview

The bot chooses a hidden word randomly from `word_power_words.txt` and users type their guesses in chat.
To aid in guessing, users may:
- ask the bot for a pronunciation, delivered via voice channel
- ask the bot for definitions, delivered via chat
- ask the bot for the [edit distance](https://en.wikipedia.org/wiki/Levenshtein_distance) between a user-supplied word and the hidden word

Following a correct guess, the bot congratulates the guesser and the process repeats.

## how to use

- add bot to server
- ask the bot for `help`
- e.g. `help pronounce`





scrapes the [American Heritage Dictionary](https://ahdictionary.com/) for pronunciations and definit
