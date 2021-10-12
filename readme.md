# Telegram animal channels
Website available: https://deer-spangle.github.io/telegram-animals/

This is a website to list all the channels on telegram which post pictures, gifs, and videos of various animals.  
I created this after I was running a few gif channels on telegram ([@deergifs](https://t.me/deergifs) and others) to see which other animals had channels posting pictures, gifs, and videos.

If you would like to add a new channel or bot, feel free to submit a pull request adding to store/telegram.json

## Directory structure
- `.github/`
  - Contains github actions workflows
- `cache/`
  - Contains cached data for channels and searches.
  - Do not manually update this, it's updated automatically by update_cache and search_handles commands
- `public/`
  - Stores the website css, and the website index on gh-pages branch.
  - Do not manually update this either, the create_html command creates it
- `scripts/`
  - One time scripts for creating session strings and such
- `store/`
  - `animals.json` Listing of all the animals and alternate names for them (for use by handle search)
  - `telegram.json` Listing of known and ignored telegram handles. Update here to add new channels.
  - `twitter.json` Listing of known twitter handles. Update here to add new twitter feeds.
- `telegram_animals/`
  - The actual code to parse, validate, and handle this data
- `main.py`
  - Entrypoint into all the scripts in telegram_animals/ Should provide help for each subcommand
