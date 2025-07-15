import io
from typing import List

from PIL import Image, ImageDraw, ImageFont
import discord
import requests

from schemas import Contestant


class Event():
    def __init__(self, description: str, groups: List[int], dead: List[tuple]):
        self.description = description
        self.groups = groups.copy()
        self.dead = dead.copy()

    def __repr__(self):
        return self.description

    def get_text(self, contestants: List[List[Contestant]]):
        string = self.description
        for i in range(0,len(self.groups)):
            groupCount = self.groups[i]
            if(len(contestants[i]) < groupCount):
                return None
            for j in range(0,groupCount):
                contestant = contestants[i][j]
                string = string.replace(f'group{i+1}{j}',contestant.name)
        return string

    def get_image(self,contestants: List[List[Contestant]]):
        height = 250
        width = 700
        s = sum(self.groups)
        if s > 5:
            width = 125*s
        
        background = Image.new('RGB', (width, height), color='black')
        draw = ImageDraw.Draw(background)
        desc = self.get_text(contestants=contestants)

        ind = 0
        profileImage = Image.new('RGB', (125*s, 100), color="black")
        for i in  range(0,len(self.groups)):
            
            for j in range(0,self.groups[i]):
                cont = contestants[i][j]
                response = requests.get(cont.picture, stream=True)
                response.raise_for_status()
                newImg = Image.open(io.BytesIO(response.content)).resize((100,100))
                if (i,j) in self.dead:

                    newImg = newImg.convert('L')
                profileImage.paste(newImg, (int(12.5+(125*ind)),0))
                ind+= 1
        background.paste(profileImage, (int((width-(s*125))/2),0))
        formatteddesc = ''
        line = ''
        titlefont = ImageFont.truetype("OpenSans-VariableFont.ttf",16)
        maxwidth = 500
        for w in desc.split():
            test = line + f'{w} '
            _, _, wid, h = draw.multiline_textbbox((0,0),test,font=titlefont, spacing=6,align='center')
            if wid > maxwidth:
                formatteddesc += f'{line}\n'
                line = f'{w} '
            else:
                line += f'{w} '
        formatteddesc+= line
        _, _, w, h = draw.multiline_textbbox((0,0),formatteddesc,font=titlefont, spacing=6,align='center')

        draw.multiline_text(((width-w)/2,(100-h)/2+150), formatteddesc,font=titlefont,fill='white',spacing=6, align='center')

        background.save(f'event-{contestants[0][0].gameid}.png')


        f = discord.File(f"event-{contestants[0][0].gameid}.png", filename=f"event-{contestants[0][0].gameid}.png")

        return f