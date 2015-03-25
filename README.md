Steam Tools
===========

Tools for inspecting the content of a Steam install. The `acf.py` tool
can read the `.acf` files and output the depots used by a game. While
the `depotscache.py` script can read the depots and list the content
of the depot.

The `depotscache.py` lists files in the same style as `sha1sum`, so it
can be used to verify the content of installed games or find out which
files don't belong into a game (i.e. manually installed mods and
stuff).

Usage is as follows:

    ./acf.py  /mnt/Program\ Files/Steam/SteamApps/appmanifest_239700.acf --depots
    239702_3148561068665061566.manifest Hate Plus
    239703_3083425136941117315.manifest Hate Plus
    239701_1543678858507212782.manifest Hate Plus

    $ ./depotcache.py --sha1sum '/mnt/Program Files/Steam/depotcache/239701_1543678858507212782.manifest'
    [? 60 98 02 ?]
    902dd7c9a9882e3c5727cfcf7991f711f10c4749 common/.DS_Store
    e8d56716a5166f74b4ad604a23afa4006232d525 common/00atl.rpy.old
    30e1016a2a8510c24e570ff1c05f5a842d3064ab common/00atl.rpyc
    e48f88e380bd2a5c56b1976cf0ff6fa330a8775c common/00compat.rpy.old
    291208176ebdded319301f64f7d090e31c89ce04 common/00compat.rpyc
    128e8029464f7c046a77513ba4c2fbfbf4f60718 common/00definitions.rpy.old
    3c23cf3f8b6a59a9d04dfc21ffefce079a5b1736 common/00definitions.rpyc
    d353f382986dbff7b791a8ee6efadbcd2bc90d95 common/00gallery.rpy.old
    24a4815f36515d1adc32d47e307816626d000b2d common/00gallery.rpyc
    9a886ac61c363b815dfa70e18b6a56d8607f437f common/00gltest.rpy.old
    2ebb7fea6c040c1ba000a4cdc054edc94150a016 common/00gltest.rpyc
    d94b224f23620172fee0cf532fe37f06337b405c common/00layout.rpy.old
    ...

This repository is build from bits and pieces from
<https://github.com/DarkStarSword/junk>.
