from operator import ge, index
from urllib import response
from flask import Flask, url_for, request, render_template, redirect, make_response
from flask_cors import CORS
from tmdbv3api import TMDb, Movie, TV, Person
from tmdbv3api.exceptions import TMDbException
from videoprops import get_video_properties, get_audio_properties
from bs4 import BeautifulSoup
from pathlib import Path
import requests, os, subprocess, configparser, socket, datetime, subprocess, socket, platform, GPUtil, json, random
from Levenshtein import distance as lev
from fuzzywuzzy import fuzz


app = Flask(__name__)
CORS(app)

tmdb = TMDb()
tmdb.api_key = 'cb862a91645ec50312cf636826e5ca1f'

config = configparser.ConfigParser()
config.read('config.ini')

if config["ChocolateSettings"]["language"] == "":
    config["ChocolateSettings"]["language"] = "en-US"

tmdb.language = config["ChocolateSettings"]["language"]
tmdb.debug = True
movie = Movie()
searchedFilms = []
simpleData = []
currentCWD = os.getcwd()
allMovies = []
allMoviesNotSorted = []
allMoviesDict = {}
hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)
config.set("ChocolateSettings", "localIP", local_ip)
filmEncode = None
CHUNK_LENGTH = 5
genreList = {
    28: "Action",
    12: "Aventure",
    16: "Animation",
    35: "Comédie",
    80: "Crime",
    99: "Documentaire",
    18: "Drama",
    10751: "Famille",
    14: "Fantastique",
    36: "Histoire",
    27: "Horreur",
    10402: "Musique",
    9648: "Mystère",
    10749: "Romance",
    878: "Science-fiction",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western",
}
genresUsed = []
movieExtension = ""
websitesTrailers = {"YouTube": "https://www.youtube.com/embed/", "Dailymotion": "https://www.dailymotion.com/video/", "Vimeo": "https://vimeo.com/"}

def getMovie(slug):
    for filmData in searchedFilms:
        if filmData["slug"] == slug:
            return filmData


def getMovies():
    movie = Movie()
    try:
        if config["ChocolateSettings"]["MoviesPath"] == "Empty":
            path = str(Path.home() / "Downloads")
        else:
            path = os.path.normpath(config["ChocolateSettings"]["MoviesPath"])
    except KeyError:
        path = str(Path.home() / "Downloads")
    os.chdir(path)
    pythonName ='python' if os.name=='nt' else 'python3'
    print("MovieServer is starting")
    subprocess.Popen([pythonName, f'{currentCWD}\movieServer.py'])

    moviesPathUrl = f"http://localhost:8000"
    pagesMovie = requests.get(moviesPathUrl)
    soupMovies = BeautifulSoup(pagesMovie.content, "html.parser")
    movies = soupMovies.find_all("a")
    filmFileList = []
    for movieFile in movies:
        filmFileList.append(movieFile.text)

    filmFileList = filmFileList
    filmFileList.sort()

    for searchedFilm in filmFileList:   
        if not isinstance(searchedFilm, str):
            continue
        if searchedFilm.endswith("/") == False and searchedFilm.endswith(("mp4", "mp4v", "mov", "avi", "flv", "wmv", "asf", "mpeg","mpg", "mkv", "ts")):
            movieTitle = searchedFilm
            originalMovieTitle = movieTitle
            size = len(movieTitle)
            movieTitle = movieTitle[:size - 4]

            try:
                search = movie.search(movieTitle)
            except TMDbException:
                print(TMDbException)
                continue
                
            if not search:
                continue
            index = filmFileList.index(searchedFilm)
            print(f"{index+1}/{len(filmFileList)}")
            
            bestMatch = search[0]
            for i in range(len(search)):
                if lev(movieTitle, search[i].title) < lev(movieTitle, bestMatch.title) and bestMatch.title not in filmFileList:
                    bestMatch = search[i]
                elif lev(movieTitle, search[i].title) == lev(movieTitle, bestMatch.title) and bestMatch.title not in filmFileList:
                    bestMatch = bestMatch
                if lev(movieTitle, bestMatch.title) == 0 and bestMatch.title not in filmFileList:
                    break
            
            res = bestMatch
            name = res.title
            movieCoverPath = f"https://image.tmdb.org/t/p/original{res.poster_path}"
            banniere = f"https://image.tmdb.org/t/p/original{res.backdrop_path}"
            description = res.overview
            note = res.vote_average
            date = res.release_date
            movieId = res.id
            details = movie.details(movieId)

            casts = details.casts.cast
            theCast = []
            for cast in casts:
                while len(theCast) < 5:
                    characterName = cast.character
                    actor = [cast.name, characterName , f"https://www.themoviedb.org/t/p/w600_and_h900_bestv2{cast.profile_path}"]
                    if actor not in theCast:
                        theCast.append(actor)
                    else:
                        break
            theBigCast = []
            for cast in casts:
                characterName = cast.character
                actor = [cast.name, characterName , f"https://www.themoviedb.org/t/p/w600_and_h900_bestv2{cast.profile_path}"]
                if actor not in theBigCast:
                    theBigCast.append(actor)
                else:
                    break

            try:
                date = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
            except ValueError:
                date = "Unknown"

            genre = res.genre_ids
            video_path = f"{path}\{originalMovieTitle}"
            # convert seconds to hours, minutes and seconds
            length = length_video(video_path)
            length = str(datetime.timedelta(seconds=length))
            length = length.split(":")

            if len(length) == 3:
                hours = length[0]
                minutes = length[1]
                seconds = str(round(float(length[2])))
                if int(seconds) < 10:
                    seconds = f"0{seconds}"
                length = f"{hours}:{minutes}:{seconds}"
            elif len(length) == 2:
                minutes = length[0]
                seconds = str(round(float(length[1])))
                if int(seconds) < 10:
                    seconds = f"0{seconds}"
                length = f"{minutes}:{seconds}"
            elif len(length) == 1:
                seconds = str(round(float(length[0])))
                if int(seconds) < 10:
                    seconds = "0"+seconds
                length = f"00:{seconds}"
            else:
                length = "0"
            
            duration = length

            for genreId in genre:
                if genreList[genreId] not in genresUsed:
                    genresUsed.append(genreList[genreId])
            
            # replace the id with the name of the genre
            movieGenre = []
            for genreId in genre:
                movieGenre.append(genreList[genreId])

            bandeAnnonce = details.videos.results
            if len(bandeAnnonce) > 0:
                for video in bandeAnnonce:
                    bandeAnnonceType = video.type
                    bandeAnnonceHost = video.site
                    bandeAnnonceKey = video.key
                    if bandeAnnonceType == "Trailer":
                        try:
                            bandeAnnonceUrl = websitesTrailers[bandeAnnonceHost] + bandeAnnonceKey
                            break
                        except KeyError as e:
                            bandeAnnonceUrl = "Unknown"
                            print(e)


            filmData = {
                "title": movieTitle,
                "realTitle": name,
                "cover": movieCoverPath,
                "banner": banniere,
                "slug": originalMovieTitle,
                "description": description,
                "note": note,
                "date": date,
                "genre": movieGenre,
                "duration": str(duration),
                "id": movieId,
                "cast": theCast,
                "theBigCast": theBigCast,
                "bandeAnnonce": bandeAnnonceUrl,
            }

            searchedFilms.append(filmData)
            simpleFilmData = {
                "title": movieTitle,
                "realTitle": name,
                "cover": movieCoverPath,
                "banner": banniere,
                "genre": movieGenre,
                "description": description,
                "slug": originalMovieTitle,
            }
            simpleData.append(simpleFilmData)
            filmDataToAppend = {
                "title": movieTitle,
                "realTitle": name,
                "cover": movieCoverPath,
                "banner": banniere,
                "slug": originalMovieTitle,
                "id": res.id,
                "description": description,
                "note": note,
            }
            allMovies.append(filmDataToAppend)
            allMoviesDict[name] = filmData


        elif searchedFilm.endswith("/") == False :
            allMoviesNotSorted.append(searchedFilm)
        



def length_video(path: str) -> float:
    seconds = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                              "default=noprint_wrappers=1:nokey=1", path], stdout=subprocess.PIPE, text=True)
    return float(seconds.stdout)

def getGpuInfo():
    if platform.system() == "Windows":
        return gpuname()
    elif platform.system() == "Darwin":
        return subprocess.check_output(['/usr/sbin/sysctl', "-n", "machdep.cpu.brand_string"]).strip()
    elif platform.system() == "Linux":
        return "impossible d'accéder au GPU"
    return ""

def gpuname():
    """Returns the model name of the first available GPU"""
    try:
        gpus = GPUtil.getGPUs()
    except:
        print("Unable to detect GPU model. Is your GPU configured? Are you running with nvidia-docker?")
        return "UNKNOWN"
    if len(gpus) == 0:
        raise ValueError("No GPUs detected in the system")
    return gpus[0].name 



@app.route("/video/<video_name>.m3u8", methods=["GET"])
def create_m3u8(video_name):
    moviesPath = config.get("ChocolateSettings", "MoviesPath")
    video_path = f"{moviesPath}\{video_name}.mkv"
    duration = length_video(video_path)
    captions = generateCaption(video_path)
    print(f"Captions : {captions}")
    file = """
    #EXTM3U
    #EXT-X-VERSION:4
    #EXT-X-TARGETDURATION:5
    """

    for i in range(0, int(duration), CHUNK_LENGTH):
        file += f"""
        #EXTINF:5.0,
        /chunk/{video_name}-{(i // CHUNK_LENGTH) + 1}.ts
        """

    file += """
    #EXT-X-ENDLIST"
    """

    response = make_response(file)
    response.headers.set("Content-Type", "application/x-mpegURL")
    response.headers.set("Content-Disposition", "attachment", filename=f"{video_name}.m3u8")

    return response

@app.route("/chunk/<video_name>-<int:idx>.ts", methods=["GET"])
def get_chunk(video_name, idx=0):
    global movieExtension
    seconds = (idx - 1) * CHUNK_LENGTH
    moviesPath = config.get("ChocolateSettings", "MoviesPath")
    video_path = f"{moviesPath}\{video_name}{movieExtension}"

    time_start = str(datetime.timedelta(seconds=seconds))
    time_end = str(datetime.timedelta(seconds=seconds + CHUNK_LENGTH))

    # check if the server as a nvidia gpu
    serverGPU = getGpuInfo()
    if serverGPU != "UNKNOWN":
        serverGPU = serverGPU.split(" ")[0]
        if serverGPU == "NVIDIA":
            videoCodec = "h264_nvenc"
            PIX = "-pix_fmt"
            PIXcodec = "yuv420p"
            preset = "3"
            bitrate = "-b:v"
            bitrateValue = "5M"
            crf = "-crf"
            crfValue = "22"
            vsync = "-vsync"
            vsyncValue = "0"
        else:
            videoCodec = "h264"
            preset = "ultrafast"

    movieVideoStats = get_video_properties(video_path)
    movieAudioStats = get_audio_properties(video_path)
    if movieAudioStats['codec_name'] == "aac" and movieVideoStats['codec_name'] == "h264":
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", time_start, "-to", time_end, "-i", video_path,
                    "-output_ts_offset", time_start, "-c:v", "copy", "-c:a", "copy", "-preset", "ultrafast", "-f", "mpegts",
                    "pipe:1"]

    elif movieAudioStats['codec_name'] == "aac" and movieVideoStats['codec_name'] != "h264":
        print(f"AudioCodec: {movieAudioStats['codec_name']}")
        print(f"VideoCoder: {movieVideoStats['codec_name']}")

        if PIX:
            command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", time_start, "-to", time_end, "-i", video_path,
                "-output_ts_offset", time_start, "-c:v", videoCodec, "-c:a", "copy", PIX, PIXcodec,"-preset", preset, bitrate, bitrateValue, crf, crfValue, vsync, vsyncValue, "-f", "mpegts", "pipe:1"]
        else:
            command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", time_start, "-to", time_end, "-i", video_path,
               "-output_ts_offset", time_start, "-c:v", videoCodec, "-c:a", "copy", "-preset", preset, "-f", "mpegts", "pipe:1"]

    elif movieAudioStats['codec_name'] != "aac" and movieVideoStats['codec_name'] == "h264":
        print(f"AudioCodec: {movieAudioStats['codec_name']}")
        print(f"VideoCoder: {movieVideoStats['codec_name']}")
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", time_start, "-to", time_end, "-i", video_path,
               "-output_ts_offset", time_start, "-c:v", "copy", "-c:a", "aac", "-preset", "ultrafast", "-f", "mpegts", "pipe:1"]
    else:
        print(f"AudioCodec: {movieAudioStats['codec_name']}")
        print(f"VideoCoder: {movieVideoStats['codec_name']}")
        if PIX:
            command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", time_start, "-to", time_end, "-i", video_path,
               "-output_ts_offset", time_start, "-c:v", videoCodec, "-c:a", "aac", PIX, PIXcodec, "-preset", preset, bitrate, bitrateValue, crf, crfValue, vsync, vsyncValue, "-f", "mpegts", "pipe:1"]
        else:
            command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", time_start, "-to", time_end, "-i", video_path,
               "-output_ts_offset", time_start, "-c:v", videoCodec, "-c:a", "aac", "-preset", preset, "-f", "mpegts", "pipe:1"]

    print((" ").join(command))

    pipe = subprocess.Popen(command, stdout=subprocess.PIPE)
    
    response = make_response(pipe.stdout.read())
    response.headers.set("Content-Type", "video/MP2T")
    response.headers.set("Content-Disposition", "attachment", filename=f"{video_name}-{idx}.ts")

    return response

@app.route("/chunkCaption/<language>/<index>/<video_name>.vtt", methods=["GET"])
def chunkCaption(video_name, language, index):
    global movieExtension
    moviesPath = config.get("ChocolateSettings", "MoviesPath")
    video_path = f"{moviesPath}\{video_name}{movieExtension}"
    extractCaptionsCommand = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", video_path, "-map", f"0:{index}", "-f", "webvtt", "pipe:1"]

    print(" ".join(extractCaptionsCommand))

    extractCaptions = subprocess.run(extractCaptionsCommand, stdout=subprocess.PIPE)

    extractCaptionsResponse = make_response(extractCaptions.stdout)
    extractCaptionsResponse.headers.set("Content-Type", "text/VTT")
    extractCaptionsResponse.headers.set("Content-Disposition", "attachment", filename=f"{video_name}-{index}.vtt")

    return extractCaptionsResponse


@app.route("/settings")
def settings():
    global allMoviesNotSorted
    condition = len(allMoviesNotSorted) > 0
    return render_template("settings.html", notSorted=allMoviesNotSorted, conditionIfOne=condition)

@app.route("/saveSettings/", methods=['POST'])
def saveSettings():
    MoviesPath = request.form['moviesPath']
    language = request.form['language']
    if MoviesPath != "":
        config.set("ChocolateSettings", "moviespath", MoviesPath)
    if language != "":
        config.set("ChocolateSettings", "language", language)
    with open(f'{currentCWD}/config.ini', 'w') as conf:
        config.write(conf)
    return redirect(url_for('settings'))

#create a route to send all the movies to the page in a json
@app.route("/getAllMovies")
def getAllMovies():
    global simpleData
    simpleData.sort(key=lambda x: x["title"].lower())
    return json.dumps(simpleData, ensure_ascii=False)

@app.route("/getRandomMovie")
def getRandomMovie():
    global simpleData
    simpleData.sort(key=lambda x: x["title"].lower())
    randomMovie = random.choice(simpleData)
    return json.dumps(randomMovie, ensure_ascii=False)

def getSimilarMovies(movieId):
    global simpleData
    similarMoviesPossessed = []
    movie = Movie()
    similarMovies = movie.recommendations(movieId)
    for movieInfo in similarMovies:
        movieName = movieInfo.title
        for movie in simpleData:
            if movieName == movie["title"]:
                similarMoviesPossessed.append(movie)
                break
    return similarMoviesPossessed

@app.route("/getMovieData/<title>", methods=['GET', 'POST'])
def getMovieData(title):
    global allMoviesDict
    if title in allMoviesDict.keys():
        data = allMoviesDict[title]
        MovieId = data["id"]
        data["similarMovies"] = getSimilarMovies(MovieId)
        return json.dumps(data, ensure_ascii=False)
    else:
        return "Not Found"

@app.route("/getFirstSevenMovies")
def getFirstEightMovies():
    global simpleData
    simpleData.sort(key=lambda x: x["title"].lower())
    return json.dumps(simpleData[:7], ensure_ascii=False)

@app.route('/')
@app.route('/index')
@app.route('/home')
def home():
    moviesPath = config.get("ChocolateSettings", "MoviesPath")
    filmIsntEmpty = moviesPath != "Empty"
    return render_template('index.html', moviesExist=filmIsntEmpty)

@app.route("/films")
def films():
    global allMoviesSorted
    searchedFilmsUp0 = len(searchedFilms) == 0
    errorMessage = "Verify that the path is correct"
    routeToUse = "/getFirstSevenMovies"

    return render_template('homeFilms.html', conditionIfOne=searchedFilmsUp0, errorMessage=errorMessage, routeToUse=routeToUse)



@app.route("/movieLibrary")
def library():
    global allMoviesSorted
    searchedFilmsUp0 = len(searchedFilms) == 0
    errorMessage = "Verify that the path is correct"
    routeToUse = "/getAllMovies"
    return render_template('allFilms.html', conditionIfOne=searchedFilmsUp0, errorMessage=errorMessage, routeToUse=routeToUse)


@app.route("/searchInAllMovies/<search>")
def searchInAllMovies(search):    
    global simpleData
    bestMatchs = {}
    movies = []
    points = {}

    for movie in simpleData:
        search = search.replace("%20", " ")
        distance = fuzz.ratio(search, movie["title"])
        points[movie["title"]] = distance

    bestMatchs = sorted(points.items(), key=lambda x: x[1], reverse=True)
    for movie in bestMatchs:
        thisMovie = movie[0]
        for films in simpleData:
            if films["title"] == thisMovie:
                movies.append(films)
                break
                
    return json.dumps(movies, ensure_ascii=False)

@app.route("/search/<search>")
def search(search):
    searchedFilmsUp0 = False
    errorMessage = "Verify your search terms"
    routeToUse = "/searchInAllMovies/" + search
    return render_template('allFilms.html', conditionIfOne=searchedFilmsUp0, errorMessage=errorMessage, routeToUse=routeToUse)


@app.route("/movie/<slug>")
def movie(slug):
    global filmEncode, movieExtension
    if slug.endswith("ttf") == False:
        movieSlug = getMovie(slug)
        rewriteSlug, movieExtension = os.path.splitext(slug)
        link = f"/video/{rewriteSlug}.m3u8".replace(" ", "%20") 
    allCaptions = generateCaption(slug)
    return render_template("film.html", movieSlug=movieSlug, slug=slug, movieUrl=link, allCaptions=allCaptions)

def generateCaption(slug):
    command = ["ffprobe", "-loglevel", "error", "-select_streams", "s", "-show_entries", "stream=index:stream_tags=language", "-of", "csv=p=0", slug]
    pipe = subprocess.Popen(command, stdout=subprocess.PIPE)
    try:
        slug = slug.split("\\")[-1]
        slug = slug.split("/")[-1]
    except:
        slug = slug.split("/")[-1]
    rewriteSlug, movieExtension = os.path.splitext(slug)
    response = pipe.stdout.read().decode("utf-8")
    response = response.split("\n")
    allCaptions = []
    languages = {
        'eng': 'English',
        'fre': 'Français',
        'spa': 'Español',
        'por': 'Português',
        'ita': 'Italiano',
        'ger': 'Deutsch',
        'rus': 'Русский',
        'pol': 'Polski',
        'por': 'Português',
        'chi': '中文',
        'srp': 'Srpski',
        }

    response.pop()
    for line in response:
        line = line.rstrip()
        language = line.split(",")[1]
        index = line.split(",")[0]
        allCaptions.append({"index": index, "languageCode" : language, "language": languages[language], "url":f"/chunkCaption/{language}/{index}/{rewriteSlug}.vtt"})
    return allCaptions

@app.route("/actor/<actorName>")
def actor(actorName):
    routeToUse = "/getActorData/" + actorName
    return render_template("actor.html", routeToUse=routeToUse)

@app.route("/getActorData/<actorName>", methods=['GET', 'POST'])
def getActorData(actorName):
    global searchedFilms, simpleData
    movies = []
    person = Person()
    actorDatas = person.search(actorName)
    for movie in searchedFilms:
        actors = movie["theBigCast"]
        for actor in actors:
            if actor[0] == actorName:
                for movieData in simpleData:
                    if movie["title"] == movieData["title"]:
                        movies.append(movie)
                        break
    actorId = actorDatas[0].id
    p = person.details(actorId)
    name = p["name"]
    image = "https://www.themoviedb.org/t/p/w300_and_h450_bestv2"+ p["profile_path"]
    birthday = p["birthday"]
    birthplace = p["place_of_birth"]
    actorDescription = p["biography"]
    actorData = {
        "actorName": name,
        "actorImage": image,
        "actorDescription": actorDescription,
        "actorBirthday": birthday,
        "actorBirthplace": birthplace,
        "actorMovies": movies
    }
    return json.dumps(actorData, default=lambda o: o.__dict__, ensure_ascii=False)

if __name__ == '__main__':
    getMovies()
    print("Starting server...")
    app.run(host="0.0.0.0", port="8500")