from toontown.chat.enums.ChatSystemMessagePreset import ChatSystemMessagePreset
from toontown.hood import ZoneUtil
from toontown.inventory.enums.ItemEnums import NameplateItemType
from toontown.toonbase import ToontownGlobals


SNOWBALL_PIE_TYPE = 10
PROGRESS_MAGIC = 0xCA000000
PROGRESS_MASK = 0xFF000000
PAYLOAD_MASK = 0x00FFFFFF

UNLOCK_MESSAGE = (
    "Congratulations! You've unlocked the Candy nameplate. "
    "You can now equip it from your Shticker book."
)

PLAYGROUND_REQUIREMENTS = (
    (ToontownGlobals.ToontownCentral, 5, 3),
    (ToontownGlobals.DonaldsDock, 8, 4),
    (ToontownGlobals.OldeToontown, 3, 2),
    (ToontownGlobals.DaisyGardens, 7, 3),
    (ToontownGlobals.MinniesMelodyland, 2, 2),
    (ToontownGlobals.TheBrrrgh, 6, 3),
    (ToontownGlobals.OutdoorZone, 1, 1),
    (ToontownGlobals.DonaldsDreamland, 4, 3),
)


def _isCandyProgressValue(value):
    return isinstance(value, int) and value & PROGRESS_MASK == PROGRESS_MAGIC


def _decodeProgress(scavengerHunt):
    payload = 0
    for value in scavengerHunt:
        if _isCandyProgressValue(value):
            payload = value & PAYLOAD_MASK
            break

    progress = {}
    shift = 0
    for playground, required, bits in PLAYGROUND_REQUIREMENTS:
        progress[playground] = min((payload >> shift) & ((1 << bits) - 1), required)
        shift += bits
    return progress


def _encodeProgress(progress):
    payload = 0
    shift = 0
    for playground, required, bits in PLAYGROUND_REQUIREMENTS:
        amount = max(0, min(int(progress.get(playground, 0)), required))
        payload |= amount << shift
        shift += bits
    return PROGRESS_MAGIC | payload


def _saveProgress(toon, progress):
    scavengerHunt = [
        value for value in toon.getScavengerHunt()
        if not _isCandyProgressValue(value)
    ]
    scavengerHunt.append(_encodeProgress(progress))
    toon.b_setScavengerHunt(scavengerHunt)


def _resetProgress(toon):
    scavengerHunt = [
        value for value in toon.getScavengerHunt()
        if not _isCandyProgressValue(value)
    ]
    toon.b_setScavengerHunt(scavengerHunt)


def _isComplete(progress):
    for playground, required, bits in PLAYGROUND_REQUIREMENTS:
        if progress.get(playground, 0) < required:
            return False
    return True


def handleSnowballThrow(toon, pieType):
    if pieType != SNOWBALL_PIE_TYPE:
        return

    zoneId = ZoneUtil.getCanonicalZoneId(toon.zoneId)

    if ZoneUtil.isInterior(zoneId):
        _resetProgress(toon)
        return

    if not ZoneUtil.isPlayground(zoneId):
        return

    requirements = dict(
        (playground, required)
        for playground, required, bits in PLAYGROUND_REQUIREMENTS
    )
    if zoneId not in requirements:
        return

    progress = _decodeProgress(toon.getScavengerHunt())
    required = requirements[zoneId]
    if progress[zoneId] < required:
        progress[zoneId] += 1
        _saveProgress(toon, progress)

    if not _isComplete(progress):
        return

    if toon.addItem(NameplateItemType.Event_Candy):
        _resetProgress(toon)
        toon.air.chatManager.sendSystemMessageToToon(
            toon.doId,
            UNLOCK_MESSAGE,
            preset=ChatSystemMessagePreset.Halloween.value,
        )
