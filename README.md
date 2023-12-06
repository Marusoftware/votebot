# Votebot
The discord bot for privating voting
## Motivation
There are no way to voting privately on discord (sometime reaction was used as an alternative).   
I think there are people don't want to reveal opinion (and may be don't want to show who vote).   
Votebot is solution of this.   
### Notice
Currently, there are Japanese messages are hardcoded. If you are not Japanese, we are sorry(I'll fix it. please wait a while). But contribution are welcome.
## Get started
There are two ways to use "Votebot".
- Use hosted one   
Please invite to your server with this URL:   
https://discord.com/api/oauth2/authorize?client_id=869004233368825939&permissions=274878123072&scope=bot%20applications.commands
- Deploy on your selfhosted server   
Please look at "Installation" section
## Usage
This bot is using "slash command".
```markdown
- /mkvote
Create vote
- /start_vote [Vote ID(optional)] [show_closed(optional)]
Starting vote
If you set show_closed true, The vote id select will show closed one, too.
- /close_vote [Vote ID(optional)] [show_user(optional)]
End vote and show result
If you set show_user true, user name will shown in the result.
- /getOpening
Show all opening vote (name and id) in guild
```
## Installation
Requirement:   
- python3.8 or later
- poetry package manager
- discord bot client keys(create in [here](https://discord.com/developers/applications))
### Install deps
```bash
git clone https://github.com/Marusoftware/votebot
cd votebot
poetry install
```
### RUN!
```
poetry run main.py [token]
```
For more command line usage, please see `poetry run main.py --help`
