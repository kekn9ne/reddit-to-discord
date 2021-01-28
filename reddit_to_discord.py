import praw
import time
import os
import requests
import json
import config
import ffmpeg
from urllib.request import urlretrieve
from discord_webhook import DiscordWebhook, DiscordEmbed

def bot_login():
    print("Loggin in.")
    r = praw.Reddit(username = config.username, password = config.password, client_id = config.client_id, client_secret = config.client_secret, user_agent = config.user_agent)
    print("Logged in.")
    return r

def run_bot(r):
    for sub in config.subreddits:
        submissions = r.subreddit(sub).hot(limit = config.limit)
        for submission in submissions:
            if submission not in blacklist:
                if submission.is_self == False:
                    if submission.is_video == True:
                        video = submission.media['reddit_video']['fallback_url']
                        audio = ""
                        if "_480." in video:
                            audio = video.replace("480", "audio")
                        elif "_720." in video:
                            audio = video.replace("720", "audio")
                        elif "_1080." in video:
                            audio = video.replace("1080", "audio")
                        else:
                            print("Found a video but it's resolution not supported.")
                            return

                        urlretrieve(video, str(submission) + ".mp4")
                        urlretrieve(audio, str(submission) + ".mp3")

                        input_video = ffmpeg.input(str(submission) + '.mp4')

                        input_audio = ffmpeg.input(str(submission) + '.mp3')

                        ffmpeg.concat(input_video, input_audio, v=1, a=1).output(str(submission) + '_merged.mp4').global_args('-loglevel', 'error').run()
                        
                        if config.remove_title_and_credits == False:
                            webhook = DiscordWebhook(url=config.webhook_url, content="**{}**\nPosted by ``u/{}`` at ``r/{}``\nTitle: ``{}``".format(config.embed_title, str(submission.author), str(submission.subreddit), str(submission.title)))
                        else:
                            webhook = DiscordWebhook(url=config.webhook_url, content=" ")
                        
                        with open(str(submission) + "_merged.mp4", "rb") as f:
                            webhook.add_file(file=f.read(), filename=submission.title + ".mp4")

                        response = webhook.execute()
                        
                        print("Sent a video to the Discord server.")

                        os.remove(str(submission) + ".mp3")
                        os.remove(str(submission) + ".mp4")
                        os.remove(str(submission) + "_merged.mp4")

                        blacklist.append(submission)
                        with open("blacklist.txt", "a") as f:
                            f.write(str(submission) + "\n")
                            f.close()

                        time.sleep(config.wait_time)
                    else:
                        if config.remove_title_and_credits == False:
                            data = {}
                            data["embeds"] = []
                            embed = {
                                    "title": config.embed_title,
                                    "author": {
                                        "name": "posted by u/{} at r/{}".format(str(submission.author), str(submission.subreddit)),
                                        "url": "https://reddit.com/r/{}/comments/{}".format(str(submission.subreddit), str(submission)),
                                        "icon_url": submission.author.icon_img
                                    },
                                    "image": {
                                        "url": submission.url
                                    },
                                    "fields": [
                                        {
                                            "name": "Post Title",
                                            "value": submission.title,
                                            "inline": False
                                        },
                                        {
                                            "name": "Author",
                                            "value": "u/{}".format(str(submission.author)),
                                            "inline": True
                                        }, 
                                        {
                                            "name": "Subreddit",
                                            "value": "r/{}".format(str(submission.subreddit)),
                                            "inline": True
                                        },
                                        {
                                            "name": "Score",
                                            "value": submission.score,
                                            "inline": False
                                        }
                                    ]
                                }
                            data["embeds"].append(embed)

                            req = requests.post(config.webhook_url, data = json.dumps(data), headers={"Content-Type": "application/json"})
                            
                            if req.status_code == 204:
                                print("Sent an image to the Discord server.")
                        else:
                            webhook = DiscordWebhook(url=config.webhook_url, content=" ")
                            embed = DiscordEmbed(title='')
                            embed.set_image(url=submission.url)
                            webhook.add_embed(embed)
                            response = webhook.execute()
                            print("Sent an image to the Discord server.")

                        blacklist.append(submission)
                        with open("blacklist.txt", "a") as f:
                            f.write(str(submission) + "\n")
                            f.close()

                        time.sleep(config.wait_time)

    

def blacklisted_posts():
    if not os.path.isfile("blacklist.txt"):
        blacklist = []
    else:
        with open("blacklist.txt", "r") as f:
            blacklist = f.read()
            blacklist = blacklist.split("\n")
            f.close()

    return blacklist

r = bot_login()
blacklist = blacklisted_posts()
while True:
    run_bot(r)
