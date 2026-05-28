# Command-Block-Assembler-for-Minecraft

This tool lets you write "assembly programs" in Python (each instruction is a Python object). It generates a chain of command blocks and outputs OOC text you can copy straight into Minecraft.

## Features

- All the execution done in one-tick (just like in datapack)

- Forward/backward jumps

- Function call/return with recursion

- Macros (dynamic nbt/scoreboard insertion, similar feature as in datapack)

- Delay instructions (like /schedule).

## How To Use

1. Download the code from this repo

2. Create a Python file in the same directory

3. Import and create a program object:

```python
from cbasm import CBAsm, Command, Macro, Goto, Call, Return, Sleep

program = CBAsm("test")  # "test" is your namespace
```

## Instruction Types

- `Command("kill @a")` - regular Minecraft command
- `Macro("say $(a1) $[a2]")` - macro command. `$(a1)` gets replaced with nbt storage, `$[a2]` gets replaced with scoreboard value
- `Goto("loop", "if score i ...")` - jump to label, optional condition
- `Call("func", "if score i ...")` - call function, records return address
- `Return("if score i ...")` - return to caller
- `Sleep(20, "if score i ...")` - delay N ticks

Use `%(obj)s` in commands to reference the current scoreboard/nbt storage name.

## CBAsm methods

- `add_instr(instr)` - add an instruction
- `add_label(label)` - add a jump label  
- `write_ooc(side_len, outfile)` - export the command block structure to OOC format. Generates a snake-like 3D layout expanding along the Z axis.

## Example Program (Counting To 1000)
```python
from cbasm import CBAsm, Command, Goto

prog = CBAsm("count")  # Define namespace as "count"
prog.add_instr(Command("say Start Counting"))
prog.add_instr(Command("scoreboard players set i %(obj)s 0"))  # %(obj)s indicates the main scoreboard objective

prog.add_label("loop")  # loop:
prog.add_instr(Command("say $[i]"))  # Macro replacement, you can also use "tellraw @a {score:{name:'i',objective:'%(obj)s'}}" here if you want better performance
prog.add_instr(Command("scoreboard players add i %(obj)s 1"))  # i += 1
prog.add_instr(Goto("loop", "if score i %(obj)s matches ..1000"))  # if i <= 1000: goto loop

prog.add_instr(Command("say Complete!"))

prog.write_ooc("output.txt")  # This will generate the ooc command
```

Run it, paste the output into a command block, and activate. If you hit chain length limits, increase `max_command_sequence_length` gamerule.

Check out `examples.py` for a prime number generator and recursive factorial.

The code isn't thoroughly tested and is a bit messy, there might be bugs. Let me know if you find any.
