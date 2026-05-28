import re


class Instr: ...


class Command(Instr):
    def __init__(self, value: str):
        self.value = value


class Macro(Instr):
    def __init__(self, value: str):
        self.value = value


class Goto(Instr):
    def __init__(self, label: str, cond: str | None = None):
        self.label = label
        self.cond = cond


class Call(Instr):
    def __init__(self, label: str, cond: str | None = None):
        self.label = label
        self.cond = cond


class Return(Instr):
    def __init__(self, cond: str | None = None):
        self.cond = cond


class Sleep(Instr):
    def __init__(self, ticks: int, cond: str | None = None):
        self.ticks = ticks
        self.cond = cond


class CBAsm:
    def __init__(self, namespace: str):
        self.objective = '.' + namespace

        self.instructions: list[Instr] = []
        self.labels: dict[str, tuple[int, int]] = {}

        self.target_score = 0
        self.chain_nbt = "auto:1b,UpdateLastExecution:0b"

        self.has_call = False
        self.has_macro = False
        self.has_sleep_aec = False

        self.ret_instr_positions: dict[str, int] = {}
    
    def add_label(self, label: str):
        self.labels[label] = (len(self.instructions), self.target_score)
        self.target_score += 1

    def add_instr(self, instr: Instr):
        if isinstance(instr, Macro):
            self.has_macro = True
        elif isinstance(instr, Sleep):
            if instr.ticks > 1:
                self.has_sleep_aec = True
        elif isinstance(instr, Call):
            # Add an unique label for return
            self.has_call = True
            self.labels[repr(instr)] = (len(self.instructions) + 1, self.target_score)
            self.target_score += 1
        elif isinstance(instr, Return):
            # Record an unique position so that we could compare it to the target score 
            # (which is poped from stack) and determine whether jump forward / backward at run time
            self.ret_instr_positions[repr(instr)] = self.target_score

        self.instructions.append(instr)

    def _process(self):
        obj = self.objective
        block_cmds: list[str] = [
            f"scoreboard objectives add {obj} dummy",
            f"scoreboard players set #skip {obj} 0"
        ]
        side_cmds: dict[int, str] = {}
        turns_right: list[int] = []
        track_outputs: list[int] = []
        impulse_cmds: list[int] = [0]

        if self.has_macro:
            block_cmds.append(
                f"execute unless entity @e[type=marker,tag={obj}] run "
                f"summon marker ~ ~ ~ {{Tags:['{obj}']}}"
            )
        
        if self.has_call:
            block_cmds.append(f"data modify storage {obj} stack set value [-1]")

        skip_prefix = ""
        max_forward_idx = -1

        forward_targets = {}
        backward_targets = {i: score for i, score in self.labels.values()}
        
        for i, instr in enumerate(self.instructions):
            if i >= max_forward_idx:
                skip_prefix = ""

            if i in forward_targets:
                target_score = forward_targets[i]
                block_cmds.append(
                    f"execute if score #goto {obj} matches {target_score} run scoreboard players set #skip {obj} 0"
                )

            if i in backward_targets:
                target_score = backward_targets[i]
                pos = len(block_cmds)
                if pos + 1 in side_cmds:
                    block_cmds.append("")
                    pos += 1
                side_cmds[pos + 1] = (
                    f"execute if score #goto {obj} matches {target_score} run "
                    f"setblock %(prev_coord)s chain_command_block[facing=east]{{{self.chain_nbt},"
                    f"Command:\"setblock ~ ~ ~ chain_command_block[facing=%(prev_dir)s]{{{self.chain_nbt}}}\"}}"
                )
                side_cmds[pos] = ""
                backward_targets.pop(i)

            if isinstance(instr, Command):
                block_cmds.append(skip_prefix + instr.value)

            elif isinstance(instr, (Goto, Call)):
                is_call = isinstance(instr, Call)

                target_idx, target_score = self.labels[instr.label]

                if is_call:
                    if instr.cond is not None:
                        prefix = f"{skip_prefix}execute {instr.cond} run "
                    else:
                        prefix = skip_prefix
                    
                    return_idx, return_score = self.labels[repr(instr)]
                    block_cmds.append(
                        f"{prefix}data modify storage {obj} stack append value {return_score}"
                    )

                    if max_forward_idx < return_idx:
                        max_forward_idx = return_idx
                    
                    forward_targets[return_idx] = return_score

                # Set #goto score
                if instr.cond is None:
                    block_cmds.append(f"{skip_prefix}scoreboard players set #goto {obj} {target_score}")
                else:
                    block_cmds.append(f"{skip_prefix}scoreboard players set #goto {obj} -1")
                    block_cmds.append(
                        f"{skip_prefix}execute {instr.cond} run scoreboard players set #goto {obj} {target_score}"
                    )

                if target_idx < i:
                    # Backward jumping
                    block_cmds.append(
                        f"execute unless score #goto {obj} matches {target_score} run "
                        f"setblock %(next_coord)s chain_command_block[facing=%(next_dir)s]{{{self.chain_nbt},"
                        f"Command:\"setblock ~ ~ ~ chain_command_block[facing=west]{{{self.chain_nbt}}}\"}}"
                    )
                    turns_right.append(len(block_cmds))
                    block_cmds.append("")
                else:
                    # Forward jumping
                    block_cmds.append(
                        f"execute if score #goto {obj} matches {target_score} run scoreboard players set #skip {obj} 1"
                    )
                    skip_prefix = f"execute if score #skip {obj} matches 0 run "
                    if max_forward_idx < target_idx:
                        max_forward_idx = target_idx
                    
                    forward_targets[target_idx] = target_score

            elif isinstance(instr, Return):
                cond_cmd = skip_prefix.rstrip(" run ") if instr.cond is None else f"{skip_prefix}execute {instr.cond}"
                if cond_cmd:
                    block_cmds.append(f"execute store result score #flag {obj} run {cond_cmd}")
                else:
                    block_cmds.append(f"scoreboard players set #flag {obj} 1")
                
                if_flag = f"execute if score #flag {obj} matches 1 run "

                # Pop stack and store the value into #goto
                block_cmds.append(f"{if_flag}execute store result score #goto {obj} run data get storage {obj} stack[-1]")
                block_cmds.append(f"{if_flag}data remove storage {obj} stack[-1]")

                ret_instr_pos = self.ret_instr_positions[repr(instr)]

                # Determine whether jump forward / backward at run time

                # Backward scenario
                block_cmds.append(
                    f"execute if score #flag {obj} matches 0 run "
                    f"setblock %(next2_coord)s chain_command_block[facing=%(next2_dir)s]{{{self.chain_nbt},"
                    f"Command:\"setblock ~ ~ ~ chain_command_block[facing=west]{{{self.chain_nbt}}}\"}}"
                )
                block_cmds.append(
                    # equilavent to '... unless score #goto {obj} matches ..{ret_instr_pos + 1} run ...'
                    f"execute if score #flag {obj} matches 1 if score #goto {obj} matches {ret_instr_pos}.. run "
                    f"setblock %(next_coord)s chain_command_block[facing=%(next_dir)s]{{{self.chain_nbt},"
                    f"Command:\"setblock ~ ~ ~ chain_command_block[facing=west]{{{self.chain_nbt}}}\"}}"
                )
                turns_right.append(len(block_cmds))
                block_cmds.append("")
                # Forward scenario
                block_cmds.append(
                    f"{if_flag}execute if score #goto {obj} matches {ret_instr_pos}.. run scoreboard players set #skip {obj} 1"
                )
                skip_prefix = f"execute if score #skip {obj} matches 0 run "
                max_forward_idx = float('inf')

            elif isinstance(instr, Macro):
                cmd = re.sub(r'\$\((\w+)\)', fr'"}},{{storage:"{obj}",nbt:"args.\1"}},{{text:"', instr.value)
                cmd = re.sub(r'\$\[(\w+)\]', fr'"}},{{score:{{name:"\1",objective:"{obj}"}}}},{{text:"', cmd)
                if instr.value == cmd:
                    raise ValueError("Macro command without interpolations")

                cmd = (
                    f'{skip_prefix}data modify block %(macro_sign_coord)s back_text.messages[0] '
                    f'set value [{{text:"{skip_prefix}{cmd}"}}]'
                )
                block_cmds.append(cmd)
                block_cmds.append(
                    f"{skip_prefix}data modify entity @e[type=marker,tag={obj},limit=1] CustomName "
                    f"set from block %(macro_sign_coord)s back_text.messages[0]"
                )

                track_outputs.append(len(block_cmds))
                block_cmds.append(f"enchant @e[type=marker,tag={obj},limit=1] lure")
                block_cmds.append(
                    f"{skip_prefix}data modify block %(next_coord)s Command set from block %(prev_coord)s "
                    "LastOutput.extra[0].extra[0].with[0]"
                )
                block_cmds.append("")
            
            elif isinstance(instr, Sleep):
                if instr.cond is not None:
                    prefix = f"{skip_prefix}execute {instr.cond} run "
                else:
                    prefix = skip_prefix

                if instr.ticks == 1:
                    if not prefix:
                        block_cmds.append("data merge block %(next_coord)s {auto:1b}")
                        impulse_cmds.append(len(block_cmds))
                        block_cmds.append("data merge block ~ ~ ~ {auto:0b}")
                    else:
                        block_cmds.append(
                            f"{prefix}setblock %(next_coord)s command_block[facing=%(next_dir)s]"
                            f"{{auto:1b,Command:'setblock ~ ~ ~ chain_command_block[facing=%(next_dir)s]"
                            f"{{{self.chain_nbt}}}'}}"
                        )
                        block_cmds.append("")
                else:
                    if not prefix:
                        block_cmds.append(
                            f"summon area_effect_cloud %(next_coord)s "
                            f"{{Age:-{instr.ticks},Duration:0,Tags:['{obj}'],WaitTime:0}}"
                        )
                        impulse_cmds.append(len(block_cmds))
                        block_cmds.append("data merge block ~ ~ ~ {auto:0b}")
                    else:
                        block_cmds.append(
                            f"{prefix}summon area_effect_cloud %(next2_coord)s "
                            f"{{Age:-{instr.ticks},Duration:0,Tags:['{obj}'],WaitTime:0}}"
                        )
                        block_cmds.append(
                            f"{prefix}setblock %(next_coord)s command_block[facing=%(next_dir)s]"
                            f"{{Command:'setblock ~ ~ ~ chain_command_block[facing=%(next_dir)s]"
                            f"{{{self.chain_nbt}}}'}}"
                        )
                        block_cmds.append("")

        return (
            block_cmds,
            side_cmds,
            turns_right,
            track_outputs,
            impulse_cmds
        )

    def write_ooc(self, side_len: int, outfile: str):
        block_cmds, side_cmds, turns_right, track_outputs, impulse_cmds = self._process()

        # Build up the main/side chains framework
        # ---------------------------------------
        height = len(block_cmds) // side_len
        x_min, y_min, z_min = 1, -2, 2
        x_max, y_max, z_max = 2, height + y_min, side_len + z_min - 1

        # main chain is on x_max
        cmds = [
            f"fill ~{x_max} ~{y_min} ~{z_min} ~{x_max} ~{y_min} ~{z_max} chain_command_block[facing=south]{{{self.chain_nbt}}}",
            f"fill ~{x_min} ~{y_min} ~{z_min} ~{x_min} ~{y_min} ~{z_max} chain_command_block{{{self.chain_nbt}}}"
        ]

        if height > 0:
            cmds.extend([
                f"clone ~{x_max} ~{y_min} ~{z_min} ~{x_max} ~{y_min} ~{z_max} ~{x_min} ~{y_min + 1} ~{z_min}",
                f"clone ~{x_min} ~{y_min} ~{z_min} ~{x_min} ~{y_min} ~{z_max} ~{x_max} ~{y_min + 1} ~{z_min}",
                f"setblock ~{x_max} ~{y_min} ~{z_max} chain_command_block[facing=up]{{{self.chain_nbt}}}",
                f"setblock ~{x_min} ~{y_min} ~{z_min} chain_command_block[facing=down]{{{self.chain_nbt}}}",
                f"clone ~{x_max} ~{y_min} ~{z_max} ~{x_max} ~{y_min} ~{z_max} ~{x_max} ~{y_min + 1} ~{z_min}",
                f"clone ~{x_min} ~{y_min} ~{z_min} ~{x_min} ~{y_min} ~{z_min} ~{x_min} ~{y_min + 1} ~{z_max}",
            ])
        if height > 1:
            height_bin = bin(height // 2)[2:]
            y = 1
            steps = len(height_bin) - 1
            for i in range(steps):
                y = 2 << i
                cmds.append(
                    f"clone ~{x_min} ~{y_min} ~{z_min} ~{x_max} ~{y_min + y - 1} ~{z_max} ~{x_min} ~{y_min + y} ~{z_min}"
                )

            y *= 2
            rest = height - y
            if rest >= 0:
                cmds.append(
                    f"clone ~{x_min} ~{y_min} ~{z_min} ~{x_max} ~{y_min + rest} ~{z_max} ~{x_min} ~{y_min + y} ~{z_min}"
                )
        
        excess = (height + 1) * side_len - len(block_cmds)
        if excess != 0:
            if height % 2 == 0:
                cmds.append(
                    f"fill ~{x_min} ~{y_max} ~{z_max - excess + 1} ~{x_max} ~{y_max} ~{z_max} air"
                )
            else:
                cmds.append(
                    f"fill ~{x_min} ~{y_max} ~{z_min} ~{x_max} ~{y_max} ~{z_min + excess - 1} air"
                )

        # Insert the commands
        # -------------------
        def get_relcoord_str(x: int, y: int, z: int) -> str:
            x_str = str(x) if x != 0 else ''
            y_str = str(y) if y != 0 else ''
            z_str = str(z) if z != 0 else ''
            return f'~{x_str} ~{y_str} ~{z_str}'

        def calc_coord(i: int, side_chain: bool = False) -> tuple[int, int, int]:
            if i < 0 or i > len(block_cmds):
                return (0, 0, 0)
            
            y = i // side_len
            if y % 2 == 0:
                z = i % side_len
            else:
                z = side_len - i % side_len - 1
            return (x_max - side_chain, y + y_min, z + z_min)
        
        def calc_direction(i: int, side_chain: bool = False) -> str:
            y = i // side_len
            if not side_chain:
                if i % side_len == side_len - 1:
                    return 'up'
                if y % 2 == 0:
                    return 'south'
                return 'north'

            if i % side_len == 0:
                return 'down'
            if y % 2 == 0:
                return 'north'
            return 'south'

        def calc_macrosign_relcoord(i: int, side_chain: bool = False) -> str:
            x, y, z = calc_coord(i, side_chain)
            mx, my, mz = 1, -2, 1
            return get_relcoord_str(mx - x, my - y, mz - z)
        
        def replace_outside_str(text, target, replacement, flags=0):
            pat = r'(["\'])(?:(?!\1)[^\\]|\\.)*\1|(' + re.escape(target) + r')'
            regex = re.compile(pat, flags)

            def repl_func(match):
                if match.group(2) is not None:
                    return replacement
                return match.group(0)

            return regex.sub(repl_func, text)

        for i in turns_right:
            coord = get_relcoord_str(*calc_coord(i))
            cmds.append(f"setblock {coord} chain_command_block[facing=west]{{{self.chain_nbt}}}")
        
        for i in track_outputs:
            coord = get_relcoord_str(*calc_coord(i))
            cmds.append(f"data merge block {coord} {{TrackOutput:1b}}")
        
        for i in impulse_cmds:
            coord = get_relcoord_str(*calc_coord(i))
            direction = calc_direction(i)
            if direction == "north":
                cmds.append(f"setblock {coord} command_block")
            else:
                cmds.append(f"setblock {coord} command_block[facing={direction}]")

        for side_chain, i_cmds in [(False, enumerate(block_cmds)), (True, side_cmds.items())]:
            for i, cmd in i_cmds:
                cmd: str

                x, y, z = calc_coord(i, side_chain)
                x_prev, y_prev, z_prev = calc_coord(i - 1, side_chain)
                x_next, y_next, z_next = calc_coord(i + 1, side_chain)
                x_next2, y_next2, z_next2 = calc_coord(i + 2, side_chain)

                next_coord = get_relcoord_str(x_next - x, y_next - y, z_next - z)
                prev_coord = get_relcoord_str(x_prev - x, y_prev - y, z_prev - z)
                next2_coord = get_relcoord_str(x_next2 - x, y_next2 - y, z_next2 - z)
                macro_sign_coord = calc_macrosign_relcoord(i, side_chain)

                next_dir = calc_direction(i + 1, side_chain)
                next2_dir = calc_direction(i + 2, side_chain)
                prev_dir = calc_direction(i - 1, side_chain)

                for target, replacement in [
                    ('%(next_coord)s', next_coord),
                    ('%(prev_coord)s', prev_coord),
                    ('%(next2_coord)s', next2_coord),
                    ('%(macro_sign_coord)s', macro_sign_coord),
                    ('%(next_dir)s', next_dir),
                    ('%(next2_dir)s', next2_dir),
                    ('%(prev_dir)s', prev_dir),
                    ('%(obj)s', self.objective),
                ]:
                    cmd = cmd.replace(target, replacement)

                for target, replacement in [
                    ('[facing=north]', ''),
                    (' run execute ', ' '),
                ]:
                    cmd = replace_outside_str(cmd, target, replacement)

                cmds.append(f"data merge block {get_relcoord_str(x, y, z)} {{Command:{cmd!r}}}")

        if self.has_macro:
            cmds.append(f"setblock ~1 ~-2 ~1 oak_wall_sign")
        
        if self.has_sleep_aec:
            cmds.append(
                f"setblock ~1 ~-2 ~2 repeating_command_block{{auto:1b,"
                f"Command:'execute at @e[type=area_effect_cloud,tag={self.objective},nbt={{Age:-1}}] run data merge block ~ ~ ~ {{auto:1b}}'}}"
            )

        oocs = self.get_ooc_from_cmds(cmds)
        with open(outfile, 'w') as f:
            f.write('\n'.join(oocs))
        
    def get_ooc_from_cmds(self, cmds: list[str]) -> list[str]:
        ooc_prefix = (
            'summon falling_block ~ ~1 ~ {BlockState:{Name:redstone_block},Time:1,Passengers:['
            '{id:falling_block,BlockState:{Name:activator_rail},Time:1,Passengers:['
        )
        ooc_suffix = (
            '{id:command_block_minecart,'
                'Command:"setblock ~ ~1 ~ command_block{auto:1b,Command:\'fill ~ ~-2 ~ ~ ~ ~ air\'}"},'
            '{id:command_block_minecart,'
                'Command:"kill @e[type=command_block_minecart,distance=..2]"}]}]}'
        )
        ooc = ooc_prefix

        oocs = []
        
        for cmd in cmds:
            passenger = f'{{id:command_block_minecart,Command:{cmd!r}}},'
            if len(ooc) + len(passenger) + len(ooc_suffix) > 32500:
                oocs.append(ooc + ooc_suffix)
                ooc = ooc_prefix + passenger
                continue
            ooc += passenger

        ooc += ooc_suffix
        oocs.append(ooc)

        return oocs
