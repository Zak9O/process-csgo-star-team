# What we focus on
We follow Andre's lead and try to focus on the dynamic behavoir of a match (one round in a game). How does CT react on the actions of T and vice versa. To limit the scope of the assignment, we have decided to only focus on the map: `de_dust2`. 

An **event log** is defined as one game (typically 16 rounds)  
A **case / trace** is defined as one round in a game (typically ends when all players in a team dies, the bomb explodes, or the bomb is diffused).

We focus on the following events

| Event                     | `concept:activity`-form | Note                                             |
| ------------------------- | ----------------------- | ------------------------------------------------ |
| A player dies             | `<team>_player_died`    |                                                  |
| A player changes location | `<team>_<location>`     | `<location>` is the location a player entered    |
| A round begins            | `round_begins`          |                                                  |
| A team wins a round       | `<team>_wins`           | See [wiki](https://wiki.alliedmods.net/Counter-Strike:_Global_Offensive_Events?fbclid=IwY2xjawNuwTJleHRuA2FlbQIxMQABHkTxGy1beTsofy9TvuZJSDMHnX5b2POzrZxWSg_UfCJr3SBGt-2R1b_cm--i_aem_ERwLfzvmQOlyg1trMs9veQ#:~:text=round%20objective-,round_end,-Name%3A) for interesting info why they win |
 
Where 
* `<team>: CT|T` is the team of the player 

# Ideas for future work
* Look at different games where we keep one team constant. 
    * Look at a game where the pro team plays noobs 
* Characterize the behavoir of a team in a round. A characterization could be something like: "they buy snipers", "they all go bombsite B", "none of them buys equipment". Then only look at the other team, and see how they react based on the simplified representation of opposing team

# Make it work on my machine

## RuM
you need to install java sdk 11 for it to work

download rum here: https://rulemining.org/ 

extract the folder whereever you want, that folder contains the SDK for java install whetever fits your IOS

open that folder in command prompt and run the following command

"C:\Program Files\Java\jdk-11\bin\java.exe" -Djava.library.path=. -jar rum-0.7.2.jar

If you get this, you most likely used the wrong Java to compile it. See the video tutorial on RuM, its good enough to understand it

![1761127379328](image/README/1761127379328.png)

## How to parse a file

Download the demo file [here](https://www.hltv.org/matches/2385919/heroic-vs-3dmax-esl-pro-league-season-22-stage-1)
![](docs/images/download-dem.png)

We have compiled a collection of Dust2 games featuring Heroic against different opponents.
The files can be found as a Zip archive [here](https://dtudk-my.sharepoint.com/:u:/g/personal/s204152_dtu_dk/EWZ-9RMrr9JFkH3LVwG1LuQBfGzFUzO_d7X534ByVL6m5Q?e=7u4coO). \
**DTU associated account required** \
Or copying this link:   
https://dtudk-my.sharepoint.com/:u:/g/personal/s204152_dtu_dk/EWZ-9RMrr9JFkH3LVwG1LuQBfGzFUzO_d7X534ByVL6m5Q?e=7u4coO


## If you use uv

You can download uv here [uv](https://docs.astral.sh/uv/#installation).

Run `uv sync` to install the necessary dependencies on your system.
To check that everything is working, do: `uv run main.py`. If it looks like the image below, you are ready to code!!
![](./docs/images/final_output.png "WTF")

