import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
from discord.utils import get
import asyncio, functools, itertools, random, youtube_dl, re
from async_timeout import timeout
from urllib import parse, request
from math import cos, radians, sqrt, ceil
from requests import get

#######################################################################################################################################################
###################### 
#######################################################################################################################################################

bot = commands.Bot(command_prefix='<', description='Bot multipropósito, desarrollado ')

youtube_dl.utils.bug_reports_message = lambda: ''

class VoiceError(Exception):
    pass

class YTDLError(Exception):
    pass

class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        webpage_url = process_info['webpage_url']
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError('Couldn\'t retrieve any matches for `{}`'.format(webpage_url))

        return cls(ctx, discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS), data=info)

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append('{} días'.format(days))
        if hours > 0:
            duration.append('{} horas'.format(hours))
        if minutes > 0:
            duration.append('{} minutos'.format(minutes))
        if seconds > 0:
            duration.append('{} segundos'.format(seconds))

        return ', '.join(duration)


#cosas de la librería
class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embed = (discord.Embed(title='Reproduciendo',
                               description='```css\n{0.source.title}\n```'.format(self),
                               color=discord.Color.blurple())
                 .add_field(name='Duración', value=self.source.duration)
                 .add_field(name='Solicitado por', value=self.requester.mention)
                 .add_field(name='Propietario', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                 .add_field(name='URL', value='[Click]({0.source.url})'.format(self))
                 .set_thumbnail(url=self.source.thumbnail))

        return embed


class SongQueue(asyncio.Queue):
    
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.loop:
                # Try to get the next song within 3 minutes.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(180):  # 3 minutes
                        self.current = await self.songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return

            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            await self.current.source.channel.send(embed=self.current.create_embed())

            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send('An error occurred: {}'.format(str(error)))
#comandos del bot para controlar música y derivados
    @commands.command(name='join', invoke_without_subcommand=True)
    async def _join(self, ctx: commands.Context):
        #summonea

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='summon')
    @commands.has_permissions(manage_guild=True)
    async def _summon(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
      
     #invoca al bot, sirve el +join también

        if not channel and not ctx.author.voice:
            raise VoiceError('No estas conectado a ningun canal de voz o servidor.')

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='leave', aliases=['disconnect'])
    @commands.has_permissions(manage_guild=True)
    async def _leave(self, ctx: commands.Context):
        

        if not ctx.voice_state.voice:
            return await ctx.send('No estoy en ningún channel.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.command(name='volume', aliases=['vol'])
    async def _volume(self, ctx: commands.Context, *, volume: int):

        if not ctx.voice_state.is_playing:
            return await ctx.send('No estoy reproduciendo música.')

        if 0 > volume > 100:
            return await ctx.send('Volumen entre 0 y 100 papá')

        ctx.voice_state.volume = volume / 100
        await ctx.send('Volumen setteado a {}%'.format(volume))

    @commands.command(name='stop', aliases=['st'])
    @commands.has_permissions(manage_guild=True)
    async def _stop(self, ctx: commands.Context):
        
        ctx.voice_state.songs.clear()

        if not ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction('⏹')

    @commands.command(name='skip', aliases=['sk'])
    async def _skip(self, ctx: commands.Context):

        if not ctx.voice_state.is_playing:
            return await ctx.send('No estoy reproduciendo nada.')

        voter = ctx.message.author
        if voter == ctx.voice_state.current.requester:
            await ctx.message.add_reaction('⏭')
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            if total_votes >= 3:
                await ctx.message.add_reaction('⏭')
                ctx.voice_state.skip()
            else:
                await ctx.send('Voto para skipear actual: **{}/3**'.format(total_votes))

        else:
            await ctx.send('Ya votaste para skippear este tema.')

    @commands.command(name='queue', aliases=['q'])
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
       

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('La cola está vacía.')

        items_per_page = 10
        pages = ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n'.format(i + 1, song)

        embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.songs), queue))
                 .set_footer(text='Viendo página {}/{}'.format(page, pages)))
        await ctx.send(embed=embed)


    @commands.command(name='loop', aliases=['lp'])
    async def _loop(self, ctx: commands.Context):
        

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nada se está reproduciendo.')

        # Inverse boolean value to loop and unloop.
        ctx.voice_state.loop = not ctx.voice_state.loop
        await ctx.message.add_reaction('✅')

    @commands.command(name='play', aliases=['p'])
    async def _play(self, ctx: commands.Context, *, search: str):
        """
        https://rg3.github.io/youtube-dl/supportedsites.html
        motores de búsqueda
        """

        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            try:
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
            except YTDLError as e:
                await ctx.send('Error al procesar la request: {}'.format(str(e)))
            else:
                song = Song(source)

                await ctx.voice_state.songs.put(song)
                await ctx.send('En cola {}'.format(str(source)))

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('No estás en un canal de voz.')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('El bot ya está en un canal de voz.')

bot.add_cog(Music(bot))

#######################################################################################################################################################
###################### 
#######################################################################################################################################################

@bot.event
async def on_ready():
    # await bot.change_presence(activity=discord.Streaming(name='Tutorials', url='http://www.twitch.tv/accountname'))
    await bot.change_presence(activity=discord.Streaming(name='AntiPasta', platform='YouTube', url='https://www.youtube.com/watch?v=dQw4w9WgXcQ'))
    print('My Ready is Body')

# @bot.event
# async def on_message(message):
#     ctx.send('Perdón Thorfiñn-kun, no estaba encendido T~T').message.channel(「💬」general)

@bot.event
async def on_message(message):
    if str(message.channel) != '「🎶」música':
        if message.content.startswith('-p'):
            await message.channel.purge(limit=2)
        elif message.content.startswith('*p'):
            await message.channel.purge(limit=2)
  
invitacion = 'https://discord.com/api/oauth2/authorize?client_id=736328464285696000&permissions=8&scope=bot'

@bot.command()
async def invit(ctx):
        await ctx.send(invitacion)

@bot.command()
async def uwu(ctx):
    await ctx.channel.send('https://imgur.com/QzrQxzG')

@bot.event
async def on_ready():
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='<help'))
        print('Estoy listo y funcionando')

@bot.command()
async def ping(ctx):
    usuario = str(ctx.author)
    embed = discord.Embed(colour=discord.Colour.dark_purple(), title=usuario + ' Pong!', description='Tardó {0} ms'.format(round(bot.latency, 1)))
    embed.set_thumbnail(url='https://images.emojiterra.com/google/android-nougat/512px/1f3d3.png')
    # print(usuario + 'Pong! {0}ms'.format(round(bot.latency, 1)))
    await ctx.send(embed=embed)

@bot.command()
async def coms(ctx):
    embed = discord.Embed(colour=discord.Colour.dark_purple(), title='Comandos', description='Lista de los comandos que este Bot acepta')
    embed.set_thumbnail(url='https://icons-for-free.com/iconfiles/png/512/checkmark+clipboard+document+list+tracklist+icon-1320167911544323810.png')
    embed.add_field(name='Comandos de música:', value=None, inline=True)
    embed.add_field(name='<play (<p)', value='Busca una pista y la reproduce', inline=False)
    embed.add_field(name='<stop (<st)', value='Detiene el bot y borra la cola de reproducción', inline=False)
    embed.add_field(name='<skip (<sk)', value='Salta a la siguiente pista', inline=False)
    embed.add_field(name='<queue (<q)', value='Muestra la cola', inline=False)
    embed.add_field(name='<loop (<lp)', value='Repite la pista o cola actual', inline=False)
    embed.set_footer(text='https://discord.com/api/oauth2/authorize?client_id=736328464285696000&permissions=8&scope=bot')
    await ctx.send(embed=embed)

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
async def sum(ctx, *, numbers: int):
    await ctx.send(float(numbers) + float(numbers))

@bot.command()
async def ptgr(ctx, a1: int, b1: int):
    h1 = sqrt(a1**2 + b1**2)
    await ctx.send(round(float(h1), 2))

@bot.command()
async def teorem_cos(ctx, a2: int, b2: int, alpha: int):
    h2 = sqrt((a2**2 + b2**2 - (2*a2*b2*cos(radians(alpha)))))
    await ctx.send(round(float(h2), 2))

# lista de memes
listaMemes = ['https://i.imgur.com/bCBt6ga.jpeg', 'https://i.imgur.com/0ooelxA.jpeg', 'https://i.imgur.com/gJ4FQ51.jpeg', 'https://i.imgur.com/uZ9SUt4.jpeg', 'https://i.imgur.com/oAChZ9A.jpeg', 'https://i.imgur.com/WkbkAFv.jpeg', 'https://i.imgur.com/YhCyLtl.jpg',  'https://i.imgur.com/wGdNHbd.jpeg', 'https://i.imgur.com/EsTgUcu.jpeg', 'https://i.imgur.com/7VO7cY6.jpeg', 'https://i.imgur.com/0LyUhow.jpeg',   'https://i.imgur.com/mtQOg4k.jpeg', 'https://i.imgur.com/pzPfY7Q.jpeg', 'https://i.imgur.com/Qw7GnHq.jpeg', 'https://i.imgur.com/0CxTCdm.jpeg', 'https://i.imgur.com/L0a52X3.jpeg', 'https://i.imgur.com/iXxawLm.jpg', 'https://i.imgur.com/NUKAipe.jpg', 'https://images3.memedroid.com/images/UPLOADED166/5f67a74322e2e.jpeg', 'https://i.imgur.com/Rq6TJyi.jpg', 'https://i.imgur.com/iEe4ezd.jpg', 'https://images7.memedroid.com/images/UPLOADED880/5f67a83ee419a.jpeg', 'https://i.imgur.com/fq4ANff.jpg', 'https://i.imgur.com/8rZ2Hod.jpg', 'https://i.imgur.com/Hqds7RA.jpg', 'https://images7.memedroid.com/images/UPLOADED642/5f664096e7b33.jpeg', 'https://i.imgur.com/rkvJE4J.jpeg', 'https://images7.memedroid.com/images/UPLOADED922/5f33da9038ac2.jpeg', 'https://i.imgur.com/cjEdM7C.jpeg', 'https://i.imgur.com/k7Tfrbs.jpeg', 'https://videos1.memedroid.com/videos/UPLOADED452/5f417fa24ce8f.mp4', 'https://images3.memedroid.com/images/UPLOADED350/5f42f5f40bcfa.jpeg', 'https://images7.memedroid.com/images/UPLOADED693/5f662dc2f2d9f.jpeg', 'https://images3.memedroid.com/images/UPLOADED152/5f551e2dc16df.jpeg', 'https://images7.memedroid.com/images/UPLOADED946/5f43cdb30e080.jpeg', 'https://images7.memedroid.com/images/UPLOADED807/5f5e8873b3354.jpeg', 'https://images7.memedroid.com/images/UPLOADED925/5f3d8c8fa2238.jpeg']

@bot.command()
async def meme(ctx):
    await ctx.send(random.choice(listaMemes))

@bot.command()
async def ip(ctx):
    ip = get('https://api.ipify.org').text
    await ctx.send('La IP del server (Minecraft 1.16.2) es: {}'.format(ip))

#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################

@bot.listen()
async def on_message(message):
    if 'tkm' in message.content.lower():
        await message.channel.send('https://i.pinimg.com/736x/5b/df/3a/5bdf3a76808b9416b549816574111829.jpg')
        await bot.process_commands(message)

@bot.listen()
async def on_message(message):
    if 'culo' in message.content.lower():
        await message.channel.send('https://i.redd.it/3elif3kis2231.jpg')
        await bot.process_commands(message)

@bot.listen()
async def on_message(message):
    if 'julian' in message.content.lower():
        await message.channel.send('Julián? Si... alejalo de las niñas')
        await bot.process_commands(message)

@bot.listen()
async def on_message(message):
    if 'avi' in message.content.lower():
        await message.channel.send('**UY MAN** es re inbancable, que se calle un rato porfa')
        await bot.process_commands(message)

@bot.listen()
async def on_message(message):
    if 'anna' in message.content.lower():
        await message.channel.send('**Wuwu**')
        await message.channel.send('https://imgur.com/QzrQxzG')
        await bot.process_commands(message)
    elif 'annie' in message.content.lower():
        await message.channel.send('**Wuwu**')
        await message.channel.send('https://media1.tenor.com/images/44a6bd0c2661c1d26a5a574190c9881d/tenor.gif?itemid=18768607')
        await bot.process_commands(message)

@bot.listen()
async def on_message(message):
    if 'hasa' in message.content.lower():
        await message.channel.send('https://imgur.com/5AjXRqE')
        await bot.process_commands(message)

@bot.listen()
async def on_message(message):
    if 'frank' in message.content.lower():
        await message.channel.send('Kalla PUTA')
        await bot.process_commands(message)
    elif 'franco' in message.content.lower():
        await message.channel.send('Kalla PUTA')
        await bot.process_commands(message)

@bot.listen()
async def on_message(message):
    if 'thorfin' in message.content.lower():
        await message.channel.send('18 pajas en un día... ni más, ni menos')
        await message.channel.send('https://media1.tenor.com/images/44a6bd0c2661c1d26a5a574190c9881d/tenor.gif?itemid=18768607')
        await bot.process_commands(message)
    elif 'cano' in message.content.lower():
        await message.channel.send('18 pajas en un día... ni más, ni menos')
        await message.channel.send('https://media1.tenor.com/images/44a6bd0c2661c1d26a5a574190c9881d/tenor.gif?itemid=18768607')
        await bot.process_commands(message)

# @bot.listen()
# async def on_message(message):
#     if 'badie' in message.content.lower():
#         await message.channel.send('Bruno? Solo hay muerte... la tuya... y la mía')
#         await bot.process_commands(message)

# token = 'NzU3MzAwNDAzOTkyNzg5MDcz.X2eY9g.vGVw4Yvcer2BsI9jlru4POD5CNM'
bot.run('NzM2MzI4NDY0Mjg1Njk2MDAw.XxtNUg.KFwVJykCXgxQ_i78e4GbwEKA-ns')
