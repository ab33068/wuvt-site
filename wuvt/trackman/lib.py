import json
import lxml.etree
import requests
import urllib
import urlparse

from wuvt import app
from wuvt import db
from wuvt import sse
from wuvt.trackman.models import Track


def stream_listeners(url):
    url += 'stats.xml'
    parsed = urlparse.urlparse(url)
    r = requests.get(url, auth=(parsed.username, parsed.password))
    doc = lxml.etree.fromstring(r.text)
    listeners = doc.xpath('//icestats/listeners/text()')[0]
    return int(listeners)


def log_track(dj_id, djset_id, title, artist, album, label, request=False,
              vinyl=False):
    track = Track(dj_id=dj_id, djset_id=djset_id, title=title, artist=artist,
                  album=album, label=label, request=request, vinyl=vinyl,
                  listeners=stream_listeners(app.config['ICECAST_ADMIN']))
    db.session.add(track)
    db.session.commit()

    # update stream metadata
    for mount in app.config['ICECAST_MOUNTS']:
        song = '{artist} - {title}'.format(artist=artist, title=title)
        requests.get(app.config['ICECAST_ADMIN'] +
                     'metadata?mount={mount}&mode=updinfo&song={song}'
                     .format(mount=urllib.quote(mount),
                             song=urllib.quote(song)))

    # update tunein
    if len(app.config['TUNEIN_PARTNERID']) > 0:
        requests.get(
            'http://air.radiotime.com/Playing.ashx?partnerId={partner_id}'
            '&partnerKey={partner_key}&id={station_id}&title={title}'
            '&artist={artist}'.format(
                partner_id=urllib.quote(app.config['TUNEIN_PARTNERID']),
                partner_key=urllib.quote(app.config['TUNEIN_PARTNERKEY']),
                station_id=urllib.quote(app.config['TUNEIN_STATIONID']),
                artist=urllib.quote(track.artist),
                title=urllib.quote(track.title)
            ))

    # update last.fm (yay!)
    if len(app.config['LASTFM_APIKEY']) > 0:
        import pylast
        import hashlib
        import time

        h = hashlib.md5()
        h.update(app.config['LASTFM_PASSWORD'])
        password_hash = h.hexdigest()

        try:
            network = pylast.LastFMNetwork(
                api_key=app.config['LASTFM_APIKEY'],
                api_secret=app.config['LASTFM_SECRET'],
                username=app.config['LASTFM_USERNAME'],
                password_hash=password_hash)
            network.scrobble(
                artist=track.artist,
                title=track.title,
                timestamp=int(time.mktime(track.datetime.timetuple())),
                album=track.album)
        except Exception as e:
            print(e)

    # send server-sent event
    sse.send(json.dumps({'event': "track_change",
                         'track': track.serialize()}))

    return track