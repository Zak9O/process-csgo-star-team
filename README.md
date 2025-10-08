# Make it work on my machine 
Download the demo file [here](https://www.hltv.org/matches/2385919/heroic-vs-3dmax-esl-pro-league-season-22-stage-1)
![](docs/images/download-dem.png)

Only consider the `heroic-vs-3dmax-m1-dust2.dem` demo file, and put it in the base of the working tree of the project
## If you use uv
You can download uv here [uv](https://docs.astral.sh/uv/#installation). 

To check that everything is working, do: `uv run main.py`. If it looks like the image below, you are ready to code!! 
![](./docs/images/final_output.png "WTF")

# Mapping Fuction (Morten and Casper)
A mapping function that takes an x- and a y-coordiante and outputs an integer id that corresponds to a zone we defined
```python
def coordinates_to_box(x: int, y: int) -> int
```
We have rudely defined the following zones on the map
![](./docs/images/map_boxes.png)
# Compressed dataframe (William and Felipe)
We want to compress the dataframe representing the game into a format we can convert into an XES log. The exact structure of the compressed dataframe will probably change, because we do not know what is required to convert the compressed dataframe into an XES log. Coordination between the compressed dataframe builders and the XES log converter creator is necessary
Each entry in the compressed dataframe could contain the following features:
```
tick, event, team
```
Where an event is either describing a player changing zones or a player dying.

# Convert Compressed Dataframe to XES log (Gabriel)
Given a compressed dataframe as defined in the previous section, create an XES log that is compatible with the tools shown in class. You will most likely have requirements to the form of the compressed dataframe, so it is necessary to coordinate with the compressed dataframe team, so they can create a dataframe you can use
