import token
import discord
from discord.embeds import Embed
from botToken import *
from discord.ext import commands
from discord.utils import get
import asyncio, random, re, os, platform
from urllib import parse, request
from math import cos, radians, sqrt
from requests import get

bot = commands.Bot(command_prefix='<', description='')

#########################################################################################################################################################
########################################################                                  ###############################################################
########################################################     [Orden de los atributos:]    ###############################################################
########################################################     (1.) Eventos                 ###############################################################
########################################################     (2.) Comandos                ###############################################################
########################################################     (3.) Listen's                ###############################################################
########################################################                                  ###############################################################
#########################################################################################################################################################

@bot.event
async def on_ready():
    bot.loop.create_task(status_task())
    print(f"""Conectado como {bot.user.name}
Version de Discord.py API: {discord.__version__}
Version de Python: {platform.python_version()}
Ejecutándose en: {platform.system()} {platform.release()} ({os.name})
-------------------------------
     Bot currently running     
-------------------------------""")
    
async def status_task():
	while True:
		
		await bot.change_presence(activity=discord.Streaming(name='Get Rickrolled!', 
															platform='YouTube', 
															url='https://www.youtube.com/watch?v=dQw4w9WgXcQ'
															))
		
		await asyncio.sleep(60)
		await bot.change_presence(activity=discord.Game("<help"))
		await asyncio.sleep(60)


# @bot.command()
# async def uwu(ctx):
#     await ctx.channel.send('https://imgur.com/QzrQxzG')

@bot.command()
async def ping(ctx):
    usuario = str(ctx.author)

    embed = discord.Embed(colour= discord.Colour.dark_purple(), 
                          title= usuario + ' Pong!', 
                          description= 'Tardó {0} ms'.format(round(bot.latency, 1))
                          )

    embed.set_thumbnail(url='https://images.emojiterra.com/google/android-nougat/512px/1f3d3.png')
    print(usuario + f'pingueó ({round(bot.latency, 1)})')
    await ctx.send(embed=embed)

# @bot.command()
# async def coms(ctx):
#     embed = discord.Embed(colour=discord.Colour.dark_purple(), title='Comandos', description='Lista de los comandos que este Bot acepta')
#     embed.set_thumbnail(url='https://icons-for-free.com/iconfiles/png/512/checkmark+clipboard+document+list+tracklist+icon-1320167911544323810.png')
#     embed.add_field(name='Comandos de música:', value=None, inline=True)
#     embed.add_field(name='<play (<p)', value='Busca una pista y la reproduce', inline=False)
#     embed.add_field(name='<stop (<st)', value='Detiene el bot y borra la cola de reproducción', inline=False)
#     embed.add_field(name='<skip (<sk)', value='Salta a la siguiente pista', inline=False)
#     embed.add_field(name='<queue (<q)', value='Muestra la cola', inline=False)
#     embed.add_field(name='<loop (<lp)', value='Repite la pista o cola actual', inline=False)
#     embed.set_footer(text='https://discord.com/api/oauth2/authorize?client_id=736328464285696000&permissions=8&scope=bot')
#     await ctx.send(embed=embed)

@bot.command()
async def youtube(ctx, *, search):
    query_string = parse.urlencode({'search_query': search})
    html_content = request.urlopen(f'http://www.youtube.com/results?{query_string}')
    #print(html_content.read().decode())
    search_results = re.findall( r'watch\?v=(\S{11})', html_content.read().decode())
    print(search_results)
    # I will put just the first result, you can loop the response to show more results
    await ctx.send('https://www.youtube.com/watch?v=' + search_results[0])

@bot.command()
async def sum(ctx, num1, num2):
    await ctx.send(float(num1) + float(num2))

@bot.command()
async def summ(ctx, num1, *args):
    total = num1
    for num in args:
        total = total + num
    await ctx.send(total)

@bot.command()
async def ptgr(ctx, a: int, b: int):
    c = a**2 + b**2
    h = sqrt(c)
    await ctx.send(round(float(h), 3))

@bot.command()
async def teorem_cos(ctx, a2, b2, alpha):
    h1 = (a2**2 + b2**2 - (2*a2*b2*cos(radians(alpha))))
    h2 = sqrt(h1)
    await ctx.send(round(float(h2), 2))
    await ctx.send(f"(sqrt({h1}))")

# @bot.command()
# async def teorem_cos(ctx, a2: int, b2: int, alpha: int):
#     h2 = sqrt((a2**2 + b2**2 - (2*a2*b2*cos(radians(alpha)))))
#     await ctx.send(round(float(h2), 2))

# lista de memes
listaMemes = [
    "https://i.imgur.com/iXxawLm.jpg" , "https://i.imgur.com/Rq6TJyi.jpg",
    "https://i.imgur.com/fq4ANff.jpg" , "https://i.imgur.com/YhCyLtl.jpg",
    "https://i.imgur.com/iEe4ezd.jpg" , "https://i.imgur.com/Hqds7RA.jpg",
    "https://i.imgur.com/NUKAipe.jpg" , "https://i.imgur.com/8rZ2Hod.jpg",
    "https://i.imgur.com/bCBt6ga.jpeg","https://i.imgur.com/rkvJE4J.jpeg",
    "https://i.imgur.com/0ooelxA.jpeg","https://i.imgur.com/gJ4FQ51.jpeg",
    "https://i.imgur.com/uZ9SUt4.jpeg","https://i.imgur.com/oAChZ9A.jpeg",
    "https://i.imgur.com/WkbkAFv.jpeg","https://i.imgur.com/wGdNHbd.jpeg",
    "https://i.imgur.com/EsTgUcu.jpeg","https://i.imgur.com/7VO7cY6.jpeg",
    "https://i.imgur.com/0LyUhow.jpeg","https://i.imgur.com/mtQOg4k.jpeg",
    "https://i.imgur.com/pzPfY7Q.jpeg","https://i.imgur.com/0CxTCdm.jpeg",
    "https://i.imgur.com/Qw7GnHq.jpeg","https://i.imgur.com/L0a52X3.jpeg",
    "https://i.imgur.com/k7Tfrbs.jpeg","https://i.imgur.com/cjEdM7C.jpeg",
    "https://images3.memedroid.com/images/UPLOADED166/5f67a74322e2e.jpeg",
    "https://images7.memedroid.com/images/UPLOADED880/5f67a83ee419a.jpeg",
    "https://images7.memedroid.com/images/UPLOADED642/5f664096e7b33.jpeg",
    "https://images7.memedroid.com/images/UPLOADED922/5f33da9038ac2.jpeg",
    "https://images3.memedroid.com/images/UPLOADED350/5f42f5f40bcfa.jpeg",
    "https://images7.memedroid.com/images/UPLOADED693/5f662dc2f2d9f.jpeg",
    "https://images3.memedroid.com/images/UPLOADED152/5f551e2dc16df.jpeg",
    "https://images7.memedroid.com/images/UPLOADED946/5f43cdb30e080.jpeg",
    "https://images7.memedroid.com/images/UPLOADED807/5f5e8873b3354.jpeg",
    "https://images7.memedroid.com/images/UPLOADED925/5f3d8c8fa2238.jpeg",
    "https://videos1.memedroid.com/videos/UPLOADED452/5f417fa24ce8f.mp4",]

@bot.command()
async def meme(ctx):
    await ctx.send(random.choice(listaMemes))

@bot.command()
async def ip(ctx):
    ip = get('https://api.ipify.org').text
    await ctx.send('La IP del server (Minecraft 1.16.4) es: {}'.format(ip))

idMara = '616453961737830430'
@bot.command()
async def momentoPuto(ctx):
    await ctx.send('Listos para lo más gei que van a ver hasta ahora?')
    # await asyncio.sleep(1.5)
    await ctx.send('Yo les avisé, que conste')
    # await asyncio.sleep(1.5)
    await ctx.send('Ahí va')
    # await asyncio.sleep(1.5)
    await ctx.send('#p https://www.youtube.com/watch?v=qbQHGVE4Vpo')
    # await asyncio.sleep(1.5)
    # await ctx.send(f'Felices 3 meses <@{idMara}>')
    embed = Embed(colour=discord.Colour.from_rgb(210, 52, 235),
                  title='Felices CUMplemes', 
                  description='Felices 3 meses bby uwu')
    embed.set_thumbnail(url='https://i.pinimg.com/originals/04/75/e9/0475e949924976f53f6f631dfe0189b1.png')
    embed.set_author(name='Hasa')
    dict = embed.to_dict()
    print('\nEmbed message send:\n',dict)
    await ctx.send(embed=embed)
    
################################################################################################################################

@bot.listen()
async def on_message(msj):
    
    if msj.content.startswith('<hasa'):
        await msj.channel.send('https://imgur.com/5AjXRqE')
        await bot.process_commands(msj)

    if msj.content.startswith('culo'):
        await msj.channel.send('https://i.redd.it/3elif3kis2231.jpg')
        await bot.process_commands(msj)

    if 'tkm' in msj.content.lower():
        await msj.channel.send('https://i.pinimg.com/736x/5b/df/3a/5bdf3a76808b9416b549816574111829.jpg')
        await bot.process_commands(msj)

    # if 'julian' in msj.content.lower():
    #     await msj.channel.send('Julián? Si... alejalo de las niñas')
    #     await bot.process_commands(msj)

    if msj.content.startswith('avi'):
        await msj.channel.send('**UY MAN** es ***re*** inbancable, que se calle un rato porfa')
        await bot.process_commands(msj)

    if msj.content.startswith('thorfin'):
        await msj.channel.send('18 pajas en un día... ni más, ni menos')
        await msj.channel.send('https://media1.tenor.com/images/44a6bd0c2661c1d26a5a574190c9881d/tenor.gif?itemid=18768607')
        await bot.process_commands(msj)
    elif msj.content.startswith('cano'):
        await msj.channel.send('18 pajas en un día... ni más, ni menos')
        await msj.channel.send('https://media1.tenor.com/images/44a6bd0c2661c1d26a5a574190c9881d/tenor.gif?itemid=18768607')
        await bot.process_commands(msj)

    # if 'badie' in msj.content.lower():
    #     await msj.channel.send('UN BUEN DEGRADÉ')
    #     await bot.process_commands(msj)

    if msj.content.startswith('nico'):
        await msj.channel.send('A')
        await bot.process_commands(msj)

    if 'invitacion' in msj.content.lower():
        await msj.channel.send(invitacion)
        await bot.process_commands(msj)

    if msj.content.startswith('sofacha'):
        await msj.channel.send('A caso te referís a Sofía? \n **SEXOOOOOOOOOOOO**')
    elif msj.content.startswith('sofi'):
        await msj.channel.send('A caso te referís a la Sofacha? \n **SEXOOOOOOOOOOOO**')

invitacion = 'https://discord.com/api/oauth2/authorize?client_id=736328464285696000&permissions=8&scope=bot'

@bot.command()
async def invit(ctx):
        await ctx.send(invitacion)

# token = 'NzU3MzAwNDAzOTkyNzg5MDcz.X2eY9g.vGVw4Yvcer2BsI9jlru4POD5CNM'
bot.run(botToken)