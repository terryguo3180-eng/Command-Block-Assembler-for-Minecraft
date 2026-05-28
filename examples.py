from cbasm import CBAsm, Command, Macro, Goto, Sleep, Call, Return


def write_ooc_find_primes():
    cbasm = CBAsm('prime')

    cbasm.add_instr(Command('scoreboard players set num %(obj)s 1000'))
    cbasm.add_instr(Command('scoreboard players set speed %(obj)s 3'))
    cbasm.add_instr(Command('scoreboard players set cnt %(obj)s 0'))
    cbasm.add_instr(Command('scoreboard players set 2 %(obj)s 2'))
    cbasm.add_instr(Command('scoreboard players set -594039 %(obj)s -594039'))
    cbasm.add_instr(Command('tellraw @a "2"'))
    cbasm.add_instr(Command('tellraw @a "3"'))
    cbasm.add_instr(Command('scoreboard players set n %(obj)s 5'))
    cbasm.add_instr(Goto('end', 'unless score n %(obj)s < num %(obj)s'))

    cbasm.add_label('sqrt(n)')
    cbasm.add_instr(Command('scoreboard players operation t0 %(obj)s = n %(obj)s'))
    cbasm.add_instr(Command('scoreboard players operation t0 %(obj)s %= 2 %(obj)s'))
    cbasm.add_instr(Goto('n+=2', 'if score t0 %(obj)s matches 0'))
    cbasm.add_instr(Command('scoreboard players operation end %(obj)s = n %(obj)s'))
    cbasm.add_instr(Command('scoreboard players operation t1 %(obj)s = end %(obj)s'))
    cbasm.add_instr(Command('scoreboard players add t1 %(obj)s 4095'))
    cbasm.add_instr(Command('scoreboard players operation t0 %(obj)s = -594039 %(obj)s'))
    cbasm.add_instr(Command('scoreboard players operation t0 %(obj)s /= t1 %(obj)s'))
    cbasm.add_instr(Command('scoreboard players operation t1 %(obj)s = t0 %(obj)s'))
    cbasm.add_instr(Command('scoreboard players add t1 %(obj)s 149'))
    cbasm.add_instr(Command('scoreboard players operation end %(obj)s /= t1 %(obj)s'))
    cbasm.add_instr(Command('scoreboard players operation end %(obj)s += t1 %(obj)s'))
    cbasm.add_instr(Command('scoreboard players operation end %(obj)s /= 2 %(obj)s'))
    cbasm.add_instr(Command('scoreboard players set i %(obj)s 3'))
    cbasm.add_instr(Goto('print(n)', 'unless score i %(obj)s <= end %(obj)s'))

    cbasm.add_label('n%i==0')
    cbasm.add_instr(Command('scoreboard players operation t0 %(obj)s = n %(obj)s'))
    cbasm.add_instr(Command('scoreboard players operation t0 %(obj)s %= i %(obj)s'))
    cbasm.add_instr(Goto('i+=2', 'unless score t0 %(obj)s matches 0'))
    cbasm.add_instr(Goto('n+=2'))

    cbasm.add_label('i+=2')
    cbasm.add_instr(Command('scoreboard players add i %(obj)s 2'))
    cbasm.add_instr(Goto('print(n)', 'unless score i %(obj)s <= end %(obj)s'))
    cbasm.add_instr(Goto('n%i==0'))

    cbasm.add_label('print(n)')
    cbasm.add_instr(Command('tellraw @a {score:{name:"n",objective:"%(obj)s"}}'))
    cbasm.add_instr(Command('scoreboard players add cnt %(obj)s 1'))
    cbasm.add_instr(Command('scoreboard players operation t0 %(obj)s = cnt %(obj)s'))
    cbasm.add_instr(Command('scoreboard players operation t0 %(obj)s %= speed %(obj)s'))
    cbasm.add_instr(Sleep(1, 'if score t0 %(obj)s matches 0'))

    cbasm.add_label('n+=2')
    cbasm.add_instr(Command('scoreboard players add n %(obj)s 2'))
    cbasm.add_instr(Goto('end', 'unless score n %(obj)s < num %(obj)s'))
    cbasm.add_instr(Goto('sqrt(n)'))

    cbasm.add_label('end')
    cbasm.add_instr(Command('tellraw @a "Complete!"'))

    return cbasm
    

def write_ooc_factorial_recursive():
    cbasm = CBAsm('factorial')

    cbasm.add_instr(Command('scoreboard players set i %(obj)s 1'))
    cbasm.add_instr(Command('scoreboard players set max %(obj)s 12'))

    cbasm.add_label('loop')
    cbasm.add_instr(Goto('end', 'unless score i %(obj)s <= max %(obj)s'))
    cbasm.add_instr(Command('scoreboard players operation n %(obj)s = i %(obj)s'))
    cbasm.add_instr(Command('scoreboard players set acc %(obj)s 1'))
    cbasm.add_instr(Call('factorial'))
    cbasm.add_instr(Call('print_result'))
    cbasm.add_instr(Command('scoreboard players add i %(obj)s 1'))
    cbasm.add_instr(Goto('loop'))

    cbasm.add_label('end')
    cbasm.add_instr(Command('tellraw @a "All done!"'))
    cbasm.add_instr(Return())

    cbasm.add_label('print_result')
    cbasm.add_instr(Command('tellraw @a [{"text":"Factorial of "},{"score":{"name":"i","objective":"%(obj)s"}},{"text":" is "},{"score":{"name":"result","objective":"%(obj)s"}}]'))
    cbasm.add_instr(Return())

    cbasm.add_label('factorial')
    cbasm.add_instr(Goto('factorial_base', 'if score n %(obj)s matches ..1'))
    cbasm.add_instr(Command('scoreboard players operation acc %(obj)s *= n %(obj)s'))
    cbasm.add_instr(Command('scoreboard players remove n %(obj)s 1'))
    cbasm.add_instr(Call('factorial'))
    cbasm.add_instr(Return())

    cbasm.add_label('factorial_base')
    cbasm.add_instr(Command('scoreboard players operation result %(obj)s = acc %(obj)s'))
    cbasm.add_instr(Return())

    return cbasm
  

if __name__ == "__main__":
    cbasm = write_ooc_find_primes()
    cbasm.write_ooc(16, "output.txt")
