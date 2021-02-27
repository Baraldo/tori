import os
import pandas
import discord
import asyncio

from discord.ext import commands
from dotenv import load_dotenv


class Row:
    tag: str
    card_code: str
    quality: str
    serial_number: int
    edition: int
    series: str
    card_name: str
    is_hurt: bool

    def __init__(self, raw_row: list):
        self.tag, self.card_code = self._parse_tag(raw_row[0])
        self.quality = self._clean(raw_row[1])
        self.serial_number = int(self._clean(raw_row[2]))
        self.edition = int(self._clean(raw_row[3]))
        self.series, self.card_name, self.is_hurt = self._parse_card(raw_row[4], raw_row[5])
        
    def _parse_tag(self, string: str):
        splited = string.split('**')
        return self._clean(splited[0]), self._clean(splited[1])

    def _parse_card(self, series: str, card_name: str):
        if '~~' in series or '~~' in card_name:
            is_hurt = True
        else:
            is_hurt = False
        return self._clean(series), self._clean(card_name), is_hurt

    def _clean(self, string: str):
        return string.replace('`', '').replace('#', '').replace('◈', '').replace('**', '').replace('~~', '').strip()


class ListParser:
    acc: list
    footers: list
    ammount: list

    def __init__(self, row: str, footer: str):
        self.acc = []
        self.footers = []
        self.ammount = self._get_ammount(footer)
        self.is_new_footer(footer)
        self.add_rows(row)

    def _parse_row(self, row: str):
        return row.split('·')

    def is_new_footer(self, footer: str):
        if footer in self.footers:
            return False
        else:
            self.footers.append(footer)
            return True

    def _get_ammount(self, footer: str):
        return footer.split()[-1]

    def is_final_page(self, footer: str):
        return self.ammount == footer.split()[-3].split('–')[1]

    def add_rows(self, content: str):
        splited = [x for x in content.splitlines() if x]
        holder = splited[0]
        for string in splited[1:]:
            self.acc.append(vars(Row(self._parse_row(string))))

    def create_file(self, user_id):
        file_name = '{0}.csv'.format(str(user_id))
        pandas.DataFrame.from_records(self.acc).drop_duplicates().to_csv(file_name, index=False)
        return file_name

    def is_complete(self):
        return len(self.footers) ==  (int(int(self.ammount) / 10) + (int(self.ammount) % 10 > 0))


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
bot = commands.Bot(command_prefix='tori')

@bot.command(name='parse', help='Wait for the green mark and flip the page!')
async def parse(ctx, msg_id: int):

    def check(rctn, user):
        return user == ctx.message.author and str(rctn.emoji) in ['➡']

    msg = await ctx.fetch_message(msg_id)
    list_parser = ListParser(msg.embeds[0].description, msg.embeds[0].footer.text)

    while not list_parser.is_final_page(msg.embeds[0].footer.text):
        await msg.add_reaction('✅')
        reaction, user = await bot.wait_for("reaction_add", check=check, timeout=100000)
        while True: 
            await msg.clear_reaction('✅')
            msg = await ctx.fetch_message(msg_id)
            if list_parser.is_new_footer(msg.embeds[0].footer.text):
                list_parser.add_rows(msg.embeds[0].description)
                await msg.add_reaction('✅')
                break
            else:
                print('sleeping')
                await asyncio.sleep(1)
          
    await msg.add_reaction('❌')
    await asyncio.sleep(2)

    if list_parser.is_complete():
        file_name = list_parser.create_file(ctx.message.author.id)
        await ctx.send('Yey! I got all the pages! Here is your file.', file=discord.File(file_name))
    else:
        await ctx.send('Something went wrong! Maybe you turned the pages too fast, wait for the green mark!')

bot.run(TOKEN)