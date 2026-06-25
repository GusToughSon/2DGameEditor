# server/guilds.py
from server.client_state import ClientState
from core.models import GuildClass, GuildMember

# Simulating memory cache of active guilds
active_guilds = {}

def create_guild(creator: ClientState, name: str, tag: str) -> bool:
    """Create a new guild, making the creator the leader."""
    char = creator.char_data
    if char.guild > 0 or len(name) < 3 or len(tag) > 5:
        return False

    guild_id = len(active_guilds) + 1
    guild = GuildClass()
    guild.name = name
    guild.tag = tag
    guild.active = 1
    guild.leader_acc_id = creator.account.data.id
    guild.leader_slot = creator.char_slot

    # Add creator as rank 0 (leader)
    leader = GuildMember()
    leader.name = char.name
    leader.acc_id = creator.account.data.id
    leader.slot = creator.char_slot
    leader.active = 1
    leader.rank = 0
    guild.members[0] = leader

    active_guilds[guild_id] = guild
    char.guild = guild_id
    char.tag = tag
    creator.recalculate_temp_stats()
    return True

def invite_to_guild(leader: ClientState, recruit: ClientState) -> bool:
    """Invites a player to join the leader's guild."""
    leader_char = leader.char_data
    recruit_char = recruit.char_data
    if leader_char.guild == 0 or recruit_char.guild > 0:
        return False

    guild = active_guilds.get(leader_char.guild)
    if not guild or guild.leader_acc_id != leader.account.data.id or guild.leader_slot != leader.char_slot:
        return False

    # Find free member slot
    for i in range(len(guild.members)):
        if guild.members[i].active == 0:
            m = guild.members[i]
            m.name = recruit_char.name
            m.acc_id = recruit.account.data.id
            m.slot = recruit.char_slot
            m.active = 1
            m.rank = 5 # recruit rank
            
            recruit_char.guild = leader_char.guild
            recruit_char.tag = guild.tag
            recruit.recalculate_temp_stats()
            return True
    return False
