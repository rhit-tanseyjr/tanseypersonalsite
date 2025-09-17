"""""
 Assembler for 32-bit RISC-V
 made for CSSE232
 John Tansey, Rishi Ramesh

"""
import string
import re
#To generate docs:
# python3 -m pdoc assembler.py -o=docs 
import sys, argparse
from enum import Enum
import pseudoinstruction_handler as ph

def main(args):
    assemble_asm(args.asm.readlines(), args)


def assemble_asm(asm_lines, args = None):
    """Takes a list of strings of assembly code. The strings san contain instructions, 
    labels, blank lines, and comments indicated with `;` (on their own line or following instructions).
    Removes comments and blanks and assembles the entire code, returning a list 
    containing binary strings of machine code."""

    #clean up the code removing comments and blanks
    print("Cleaning comments...")
    asm_list = comments_pass(asm_lines)

    #process the pseudoinstruction defninition
    print("Processing pseudoinstructions...")
    pseudos = ph.get_pseudoinstruction_defs()
    core_asm = pseudoinstruction_pass(asm_list, pseudos)

    #extract the labels
    print("Creating labels...")
    clean_code, labels = parse_labels(core_asm)

    #assemble each line
    print("Translating to machine code...")
    machine_code = machine_pass(clean_code, labels)
    
    #output the code
    #set out=None to print to console
    print("Outputting...")
    mode = None
    out = None
    if(args):
        out = args.out
        if(args.verbose):
            mode = None
        else:
            mode = args.mode
    output(machine_code, clean_code, labels, mode = mode, out = out)

    print("Done.")
    return machine_code

##############
#
# Helpers which define the major passes of the assembler 
#
##############
def comments_pass(asm_lines):
    """Takes in a list representing the contents of an asm file.
        Returns a new list with comments and blank lines removed from the list."""
    asm_list = []
    for line in asm_lines:
        line = remove_comments(line.lstrip())
        if(line == None):
            continue
        asm_list.append(line)
    return asm_list

def pseudoinstruction_pass(asm_lines, pseudos_dictionary):
    """Takes in a list of assembly instructions (with no comments, labels are okay) 
        and returns a new list where any pseudoinstructions are replaced with their 
        equivalent core instructions."""
    
    newLines = []


    for i in range(len(asm_lines)):
        line = asm_lines[i]  # Get the current line
        label, instr = split_out_label(line)
        command = instr.split()[0]  # Extract the command (e.g., "diffsums")

        if(has_label(line)):
            command = instr.split()[0]


        if command in pseudos_dictionary:
            # Expand pseudo-instruction
           
            expanded_lines = pseudos_dictionary[command](instr, i)
            # Append expanded lines to newLines
            newLines.extend(expanded_lines)
        else:
            newLines.append(line)

    return newLines

def machine_pass(asm_lines, labels_dictionary):
    """Taken in a list of assembly lines with no comments or pseudoinstructions. 
        Returns a list containing the binary machine translation of each line."""
    machine_code = []
    for i, line in enumerate(asm_lines):
        result = Assemble(line, i, labels_dictionary)
        machine_code.append(result)

    return machine_code

##############
#
# Actual Assembler Methods
#
##############
def Assemble(inst, line_num=0, labels=None):
    """Takes an instruction as a string, splits it into parts, and then calls the correct helper
        to assemble it, returning the result.
        The optional parameter `labels` should be a Dictionary mapping Label strings 
        to addresses.
        
        This function and the helpers should raise exceptions when invalid instructions are
        encountered. See the exceptions types defined below in this file, they are all named 
        `BadX` where X is a particular kind of error (e.g. `BadImmediate`). 

        Some test cases rely on these errors being raised at appropriate times. 

        This function (and each of the helpers) should return a binary string with bits in groups of 4
        separated by a space character:

        `0000 1111 0000 1111 0000 1111 0000 1111`

        The spacing is intended to make debugging easier.
        """

    split_inst = inst.strip().replace(",", " ").split()
    cmd = split_inst[0]
    args = split_inst[1:]


    type = inst_to_types.get(cmd)

    # index_to_address(4)
    result = ""
    match type:
        case Types.R:
            result = Assemble_R_Type(cmd, args, line_num)
        case Types.I:
            if(cmd == 'lw' or cmd == "jalr"):
                result = Assemble_I_Type_base_offset(cmd, args, line_num)
            else:
                result = Assemble_I_Type(cmd, args, line_num)
        case Types.S:
            result = Assemble_S_Type(cmd,args,line_num) 
        case Types.U:
            result = Assemble_U_Type(cmd, args, line_num)  
        case Types.UJ:
            result = Assemble_UJ_Type(cmd, args, line_num,labels) 
        case Types.SB:
            result = Assemble_SB_Type(cmd, args, line_num,labels )      
    return result

def Assemble_R_Type(cmd, operands, line_num):
    """Takes an R Type instruction name and its operands (as a list) and 
        returns the appropriate binary string. A basic call would look like:
        
        `Assemble_R_Type("add", ["t0", "t1", "x2"], 0)`
        
        You may want to consider implementing `verify_field_sizes` that will
        take a list of binary values and make sure each one is the right size
        for the field (funct7, etc). Using it here and in all future
        instruction types may help in debugging.

        Raises BadInstruction exception when the cmd is not a valid R-type.

        Raises BadOperands exception when the wrong number of operands is
        provided or if base-offset notation is used.

        Raises BadRegister exception if one of the operands provided is not a
        valid register name (e.g., it is an immediate or label)
    """

    if(len(operands) != 3):
        raise BadOperands("Incorrect number of operands found in R Type on line %s with args:\n\t%s %s\n" % (line_num, cmd, operands))

    field_data = inst_to_fields[cmd]

    rd  = get_register_bin(operands[0])
    rs1 = get_register_bin(operands[1])
    rs2 = get_register_bin(operands[2])

    if(not is_register_name(operands[2])):
        raise BadRegister()
    
    if(not is_register_name(operands[1])):
        raise BadRegister()
    
    if(not is_register_name(operands[0])):
        raise BadRegister()

    inst_field_list = [field_data.func7,
                       rs2,
                       rs1,
                       field_data.func3,
                       rd, 
                       field_data.opcode]

    return join_inst_fields_bin(inst_field_list)

def Assemble_I_Type(cmd, operands, line_num):
    """Takes an I Type instruction name and its operands (as a list) and 
        returns the appropriate binary string.

        Raises BadInstruction exception when the cmd is not a valid I-type.

        Raises BadOperands exception when the wrong number of operands is
        provided

        Raises BadRegister exception if one of the operands in a register
        position (rd or rs1) is not a valid register name

        Raises BadImmediate exception when the value provided does not fit in
        the instruction's immediate space.
    """



    if(len(operands) != 3):
        raise BadOperands("Incorrect number of operands found in R Type on line %s with args:\n\t%s %s\n" % (line_num, cmd, operands))
    
    if(not is_core_inst(cmd)):
        raise BadInstruction()
    
    field_data = inst_to_fields[cmd]

    rd  = get_register_bin(operands[0])
    rs1 = get_register_bin(operands[1])
    imm = dec_to_bin(operands[2], size = 12)

    

    inst_field_list = [imm,
                       rs1,
                       field_data.func3,
                       rd, 
                       field_data.opcode]

    return join_inst_fields_bin(inst_field_list)
    


def Assemble_I_Type_shift(cmd, operands, line_num):
    """Takes an I Type instruction name and its operands and returns 
        the appropriate binary string.

        Replaces `imm[11:5]` with the "func7" bits for the instructions defined 
        by the green sheet.
        
        Note: recall that the rightmost bit in a RISC-V immediate is index 0,
        but python indexes strings left to right, so in a 12 bit immediate
        the rightmost bit in RISC-V is index 0 but in python that same bit
        is index 11.

        Raises BadInstruction exception when the cmd is not a valid I-type
        shift.

        Raises BadOperands exception when the wrong number of operands is
        provided

        Raises BadRegister exception if one of the operands in a register
        position (rd or rs1) is not a valid register name

        Raises BadImmediate exception when the value provided is negative or
        greater than 31.
        """


    if(int(operands[2]) < 0 or int(operands[2]) > 13):
        raise BadImmediate("Immediate value outside of bounds")

    if(len(operands) != 3):
        raise BadOperands("Incorrect number of operands found in R Type on line %s with args:\n\t%s %s\n" % (line_num, cmd, operands))
    
   
    if(not is_core_inst(cmd)):
        raise BadInstruction()
    
    
    

    field_data = inst_to_fields[cmd]

    rd  = get_register_bin(operands[0])
    rs1 = get_register_bin(operands[1])
    imm = dec_to_bin(operands[2], size = 12)

    if(cmd == "srai"):
        imm = '010000' + imm[6:13]

    

    inst_field_list = [imm,
                       rs1,
                       field_data.func3,
                       rd, 
                       field_data.opcode]

    return join_inst_fields_bin(inst_field_list)

def Assemble_I_Type_base_offset(cmd, operands, line_num):
    """Takes the operands for a lw or jalr instruction and returns the 
        appropriate binary string. You may want to implement and use
        the `parse_base_offset` helper method before writing this code.

        Note that the following are valid syntax for base-offset instructions (like jalr):
            jalr x0, 4 (ra)  // <- space betwen 4 and (ra)
            jalr x0, ra, 4   // <- standard I-type format
            jalr x0, 4(ra)   // <- no space between offset and base
        
        Raises BadInstruction exception when the cmd is not a valid I-type
        base-offset instruction.

        Raises BadOperands exception when the wrong number of operands is
        provided.

        Raises BadRegister exception if one of the operands in a register
        position is not a valid register name.

        Raises BadImmediate exception when the value provided will not fit in
        the immediate space for the instruction or if there is a register
        specifier in the immediate operand location.
 """



    if(not is_core_inst(cmd)):
        raise BadInstruction()
    
    if(len(operands) != 2 and cmd != "jalr"):
        raise BadOperands()
    if (cmd == 'jalr') and len(operands) == 3:
        if operands[2].isdecimal() and not operands[1].isdecimal():
            operands[1], operands[2] = operands[2], operands[1]

            if not (operands[2].startswith('(') and operands[2].endswith(')')):
                operands[2] = f"({operands[2]})"



    if(cmd == "jalr" and len(operands) == 3):
        rs1 = parse_base_offset(operands[1] + operands[2])[1]
 
    else:
        rs1 = parse_base_offset(operands[1])[1]

    rd = get_register_bin(operands[0])

    if(operands[1][0] == '-'):
        imm = dec_to_bin(operands[1][0:2], size = 12)

    else:
        imm = dec_to_bin(operands[1][0], size = 12)


 
    
    field_data = inst_to_fields[cmd]

    inst_field_list = [imm,
                       rs1,
                       field_data.func3,
                       rd, 
                       field_data.opcode]

    return join_inst_fields_bin(inst_field_list)
    

def Assemble_I_Type_from_fields(imm, rs1, func3, rd, opcode, line_num):
    """Helper function for I Types to be called after the immediate has 
        been processed by the main I Type functions."""

    return "0000 0000 0000 0000 0000 0000 0000 0000"

def Assemble_S_Type(cmd, operands, line_num):
    """Takes the operands for an S Type instruction and returns the 
        appropriate binary string.

        Raises BadInstruction exception when the cmd is not a valid S-type
        instruction.

        Raises BadOperands exception when the wrong number of operands is
        provided.

        Raises BadRegister exception if one of the operands in a register
        position is not a valid register name.

        Raises BadImmediate exception when the value provided will not fit in
        the immediate space for the instruction or if there is a register
        specifier in the immediate operand location.
    """


    if(not is_core_inst(cmd)):
        raise BadInstruction()
    
    if(len(operands) != 2):
        raise BadOperands()
      
 
    rs2 = get_register_bin(operands[0])

    if(operands[1][0] == '-'):
        rs1 = get_register_bin(operands[1].split('(')[1].rstrip(')'))
        if(rs1.isdigit == False):
            raise BadRegister()
    else:
        rs1 = get_register_bin(operands[1].split('(')[1].rstrip(')'))
        if(rs1.isdigit == False):
            raise BadRegister()

    if(operands[1][0] == '-'):
        imm = dec_to_bin(operands[1].split('(')[0], size = 12)
        # if(operands[1][0:2] < -(2^11)):
        #     raise BadImmediate()
    else:
        imm = dec_to_bin(operands[1].split('(')[0], size = 12)
        # if(operands[1][0] > 2^11-1):
        #     raise BadImmediate()

   # if(int(imm) > 2^11-1 or int(imm) < -(2^11)):
    #    raise BadImmediate()

    firstBits = imm[:7]
    secondBits = imm[7:]
    
    field_data = inst_to_fields[cmd]

    inst_field_list = [firstBits,
                       rs2,
                       rs1,
                       field_data.func3,
                       secondBits, 
                       field_data.opcode]

    return join_inst_fields_bin(inst_field_list)

def format_address(address):
    register = address[0]
    offset = address[1:]
    return f"{offset}({register})"

def Assemble_SB_Type(cmd, operands, line_num, labels=None):
    """Takes an SB Type instruction name and its operands (as a list) 
        and returns the appropriate binary string. 
        
        This method assumes that if a number is passed in as the 
        third operand (`operands[2]`) it is the PC offset, not the immediate. 
        Therefore the offset will be right-shifted before the immediate is generated.
        
        If a non-integer is passed in instead then this method
        expects that to be a label who's address is specified in the `labels`
        dictionary. 
        
        In both cases the `line_num` is used to calculate the immediate from
        the offset. You should assume that a `line_num` equal to 0 indicates
        an instruction at the beginning of the text segment of memory. 
        
        You should consider writing and using the `index_to_address` and
        `label_to_offset` methods for use in this instruction type (and others).

        Raises BadInstruction exception when the cmd is not a valid SB-type.

        Raises BadOperands exception when the wrong number of operands is
        provided.

        Raises BadRegister exception if one of the operands in a register
        position is not a valid register name.

        Raises BadImmediate exception when the value provided will not fit in
        the immediate space for the instruction or if there is a register
        specifier in the immediate operand location.
        """


    if(not is_core_inst(cmd)):
        raise BadInstruction()
    
    if(len(operands) == 3):
        offset = operands[2]
        if(offset.isdecimal() or offset[0] == '-'): 
            imm = (dec_to_bin(int(offset) >> 1))
        elif(is_register_name(offset)):
            raise BadImmediate()
        else:
            imm = dec_to_bin(int(label_to_offset(labels, offset, line_num)) >> 1)
    elif(len(operands) == 2):
        imm = 0
    else:
        raise BadOperands()
      
    rs1 = get_register_bin(operands[0])
    rs2 = get_register_bin(operands[1])

    # if(int(imm) > 2**20-1 or int(imm) < -2**20):
    #     raise BadImmediate()

    # if(operands[1][0] == '-'):
    #     rs1 = get_register_bin(operands[1].split('(')[1].rstrip(')'))
    #     if(rs1.isdigit == False):
    #         raise BadRegister()
    # else:
    #     rs1 = get_register_bin(operands[1].split('(')[1].rstrip(')'))
    #     if(rs1.isdigit == False):
    #         raise BadRegister()

    # if(operands[1][0] == '-'):
    #     imm = dec_to_bin(operands[1].split('(')[0], size = 12)
    #     # if(operands[1][0:2] < -(2^11)):
    #     #     raise BadImmediate()
    # else:
    #     imm = dec_to_bin(operands[1].split('(')[0], size = 12)
        # if(operands[1][0] > 2^11-1):
        #     raise BadImmediate()

   # if(int(imm) > 2^11-1 or int(imm) < -(2^11)):
    #    raise BadImmediate()

    # if(is_int(operands[2])):
    #     if(int(operands[2]) < -(2**12) or int(operands[2]) > 2**11-1):
    #             raise BadImmediate("Immediate value outside of bounds")
        
    #     offset = int(operands[2])
    # else:
    #     if(is_register_name(operands[2])):
    #         raise BadImmediate()
    #     offset = label_to_offset(labels, operands[2], line_num)
    

    # imm = dec_to_bin(offset >> 1, 12)

    # imm = str(imm)

    firstBits = imm[0]
    secondBits = imm[2:8]
    thirdBits = imm[8:12]
    lastBits = imm[1]
    
    field_data = inst_to_fields[cmd]

    first_imm = firstBits + secondBits

    inst_field_list = [first_imm,
                       rs2,
                       rs1,
                       field_data.func3,
                       thirdBits + lastBits, 
                       field_data.opcode]

    return join_inst_fields_bin(inst_field_list)
        

def Assemble_U_Type(cmd, operands, line_num):
    """Takes an U Type instruction name and its operands 
        (as a list) and returns the appropriate binary string.

        Raises BadInstruction exception when the cmd is not a valid U-type.

        Raises BadOperands exception when the wrong number of operands is
        provided.

        Raises BadRegister exception if the operand in a register
        position is not a valid register name.

        Raises BadImmediate exception when the value provided will not fit in
        the immediate space for the instruction or if there is a register
        specifier in the immediate operand location.
    """

   
    if(not is_core_inst(cmd)):
        raise BadInstruction()
    
    if(len(operands) != 2):
        raise BadOperands()
    
    if(operands[0][0] == '-'):
        rd = get_register_bin(operands[0])
        # if(rs1.isdigit == False):
        #     raise BadRegister()
    else:
        rd = get_register_bin(operands[0])
        # if(rs1.isdigit == False):
        #     raise BadRegister()
        
    if(operands[1][0] == '-'):
        if(operands[1][1:].isdecimal()):
            if(int(operands[1]) < -524288 or int(operands[1]) > 524287):
                raise BadImmediate("Immediate value outside of bounds")
        else:
            raise BadImmediate()
    else:
        if(operands[1].isdecimal()):
            if(int(operands[1]) < -524288 or int(operands[1]) > 524287):
                raise BadImmediate("Immediate value outside of bounds")
        else:
            raise BadImmediate()
    
    imm = dec_to_bin(operands[1], size = 20)

    
    field_data = inst_to_fields[cmd]

    inst_field_list = [imm,
                       rd,
                       field_data.opcode]

    return join_inst_fields_bin(inst_field_list)
    


def Assemble_UJ_Type(cmd, operands, line_num, labels):
    """Takes an UJ Type instruction name and its operands 
        (as a list) and returns the appropriate binary string.

        This method assumes that if a number is passed in as 
        the third operand (`operands[2]`) it is the PC offset, 
        not the immediate. Therefore the offset will be 
        right-shifted before the immediate is generated. 
        Otherwise it is assumed to be a label defined in `labels`.

        Raises BadInstruction exception when the cmd is not a valid UJ-type.

        Raises BadOperands exception when the wrong number of operands is
        provided.

        Raises BadRegister exception if one of the operands in a register
        position is not a valid register name.

        Raises BadImmediate exception when the value provided will not fit in
        the immediate space for the instruction or if there is a register
        specifier in the immediate operand location.

        Raises BadLabel exception if the immediate operand provided is a label
        but it is not defined in the `labels` dictionary.
    """
        
    if(not is_core_inst(cmd)):
        raise BadInstruction()
    
    if(len(operands) != 2):
        raise BadOperands()
    
    if(operands[0][0] == '-'):
        rd = get_register_bin(operands[0])
        # if(rs1.isdigit == False):
        #     raise BadRegister()
    else:
        rd = get_register_bin(operands[0])
        # if(rs1.isdigit == False):
        #     raise BadRegister()
   
    if(is_int(operands[1])):
        if(int(operands[1]) < -2**20 or int(operands[1]) > 2**20-1):
                raise BadImmediate("Immediate value outside of bounds")
        
        offset = int(operands[1])
    else:
        if(is_register_name(operands[1])):
            raise BadImmediate()
        offset = label_to_offset(labels, operands[1], line_num)
    

    imm = dec_to_bin(offset >> 1, 20)

    first_bit = imm[0]          
    second_bits = imm[1:9]     
    third_bit = imm[9]         
    fourth_bits = imm[10:20]    

    total_imm = first_bit + fourth_bits + third_bit + second_bits
    
    field_data = inst_to_fields[cmd]

    inst_field_list = [total_imm,
                       rd,
                       field_data.opcode]

    return join_inst_fields_bin(inst_field_list)

##############
#
# Comments, Labels, and other sugar
#
##############

def remove_comments(line):
    """Takes a line of assembly and removes any text after a comment character (`;`).\
        Returns `None` if line is entirely a comment."""
    #removes comment lines or blank lines
    line = line.lstrip()
    if(line.startswith(";") or not line.rstrip()):
        return None
    sline = line.split(";")
    return sline[0]

def parse_labels(asm_list):
    """Takes in a list where each entry is either a label, an instruction, 
        or a label and an instruction. Assumes there are no comments in this code.
        Returns a tuple containing a new list of only instructions (the labels 
        having been removed), and a dictionary mapping labels to addresses
        in the instruction list."""
    

    instructions = []
    label_dict = {}
    address = 0x00400000 # Address index starts at 0 and increments per instruction
    
    for line in asm_list:
        # Split the line into potential label and instruction
        parts = line.split(":", maxsplit=1)
        
        if len(parts) == 2:
            # If there's a label, map it to the current address
            label = parts[0].strip()

            if( label in label_dict.keys()):
                raise BadLabel()
            
            label_dict[label] = address
            
            # Check if there's an instruction after the label
            instruction = parts[1].strip()
            if instruction:
                instructions.append(instruction)
                address += 0X4
        else:
            # No label, just an instruction
            instruction = parts[0].strip()
            instructions.append(instruction)
            address += 0X4
    
    return instructions, label_dict

def index_to_address(index):
    """Given a line number or index in a program returns the RISC-V address
      of the instruction, assuming the program starts at the beginning 
      of the text segment of memory."""

    pc = 0x00400000
    address = pc + index * 4
    return address

def label_to_offset(labels, label, instruction_index):
    """Takes in the dictionary of labels, a label of interest and a 
        current instruction-index (not an address). Returns the byte offset between 
        the label and PC calculated from the instruction index."""

    if(len(labels) == 0):
        pointer = 0x00400000

    elif(label not in labels):
        raise BadLabel()
    
    else:
        pointer = labels[label]
    
    # Calculate the instruction offset
    instruction_offset = index_to_address(instruction_index)
    
    # Convert instruction offset to byte offset (each instruction is 4 bytes)
  #  byte_offset = instruction_offset * 4
    
    return pointer - instruction_offset

def split_out_label(line):
    """Takes a line of raw assembly code and splits any label from the beginning
    of the line.  Returns a tuple of label and instruction, either of which
    could be None (if they don't exist).

    Will return (str, None) if there's a label alone on the line.
    Will return (None, str) if there's no label on the line.
    Will return (str, str) if there's both a label and code on the line.
    Or it might return (None, None) if there's no label or instruction.
    """

    clean = line.strip()
    
    # case 1: line is exclusively a label (and whitespace)
    # case 2: line has a label and maybe an instruction
    if ":" in clean:
        # this is a sneaky one-liner to do the same thing
        #[label, inst] = [x.strip() if len(x.strip()) > 0 else None for x in line.split(":",1)]
        [label, inst] = line.split(":", 1)
        label = label.strip()
        inst = inst.strip() if len(inst.strip()) > 0 else None
        if(len(label.split()) > 1): raise BadLabel("Whitespace chars disallowed in labels")
        return (label, inst)
    
    # case 3: no label, return only the code
    return (None, clean)


def has_label(line):
    """Takes a line of raw assembly code, and returns True if the line either
    *is* or contains a label."""
    (label, inst) = split_out_label(line)
    return label is not None


##############
#
# Output 
#
##############

def output(machine_code, clean_code, labels, mode = None, out = None):
    """Takes in two lists, the first a list of binary machine translations,
    the second a list containing the raw assembly associated with each 
    instruction (no comments or blank lines).

    These two lists must be the same size.

    Also takes in the labels dictionary to add labels to the output.

    If `out` is None then the output is printed to the console, otherwise
    the output is written to the file specified by the `out` parameter.

    If mode is `None` then outputs binary with hex and raw assembly in comments.

    If mode is `bin` then outputs binary with raw assembly in comments (no hex).

    If mode is `hex` outputs hex with raw assembly in comments (no binary).

    Addresses of each instruction are always printed in the comments.
    """
    i = int("00400000", 16)
    address_to_label = {v:k for (k,v) in labels.items()}
    for m, c in zip(machine_code, clean_code):
        label = "\t"
        if(i in address_to_label):
            label = address_to_label[i] + ":\t"
        if(not mode):
            s = ("%s // 0x%s ;;; %s - %s%s " % (m, bin_to_hex(m), hex(i), label, c.rstrip()))
        elif (mode == "bin"):
            s = ("%s // %s - %s%s " % (m, hex(i), label, c.rstrip()))
        else:
            s = ("%s // %s - %s%s " % (bin_to_hex(m), hex(i), label, c.rstrip()))

        if(out):
            out.write(s+"\n")
        else:
            print(s)
        i += 4

##############
#
# Utilities 
#
##############

#Enum of Types
Types = Enum("Types", ["R", "I", "S", "SB", "U", "UJ", "PSEUDO"])
"""Enum of instruction Types"""

#dictionary mapping instruction name to types
inst_to_types = {#R types
                "add":Types.R, "sub":Types.R, "xor":Types.R, "or":Types.R, "and":Types.R, "sll":Types.R,
                "srl":Types.R, "sra":Types.R, "slt":Types.R, 
                #I Types and S Types
                "addi":Types.I, "xori":Types.I, "ori":Types.I, "andi":Types.I, "slli":Types.I, "srli":Types.I,
                "srai":Types.I, "lw":Types.I, "sw":Types.S, "jalr":Types.I,
                #SB Types
                "beq":Types.SB, "bne":Types.SB, "blt":Types.SB, "bge":Types.SB, 
                #U and UJ Types
                "jal":Types.UJ, "lui":Types.U
                }
"""Dictionary mapping instruction name to types"""

class FieldData():
    """
    Struct to hold data for different fields of instructions.
    """
    def __init__(self, opcode, func3=None, func7=None):
        self.opcode = opcode
        self.func7 = func7
        self.func3 = func3
        

#dictionay mapping instruction name to the different fields as a FieldData object
inst_to_fields = {#R types
                "add":FieldData("0110011", "000", "0000000"), 
                "sub":FieldData("0110011", "000", "0100000"), 
                "xor":FieldData("0110011", "100", "0000000"), 
                "or": FieldData("0110011", "110", "0000000"), 
                "and":FieldData("0110011", "111", "0000000"), 
                "sll":FieldData("0110011", "001", "0000000"),
                "srl":FieldData("0110011", "101", "0000000"), 
                "sra":FieldData("0110011", "101", "0100000"), 
                "slt":FieldData("0110011", "010", "0000000"), 
                #I Types and S Types
                "addi":FieldData("0010011", "000"), 
                "xori":FieldData("0010011", "100"), 
                "ori": FieldData("0010011", "110"), 
                "andi":FieldData("0010011", "111"), 
                "slli":FieldData("0010011", "001"), 
                "srli":FieldData("0010011", "101"),
                "srai":FieldData("0010011", "101"), 
                "lw":  FieldData("0000011", "010"), 
                "sw":  FieldData("0100011", "010"), 
                "jalr":FieldData("1100111", "000"),
                #SB Types
                "beq":FieldData("1100011", "000"), 
                "bne":FieldData("1100011", "001"), 
                "blt":FieldData("1100011", "100"), 
                "bge":FieldData("1100011", "101"), 
                #U and UJ Types
                "jal":FieldData("1101111"), 
                "lui":FieldData("0110111")
                }
"""Dictionay mapping instruction name to the different fields as a FieldData object"""

#dictionary that maps register names to their ID numbers (in decimal)
register_name_to_num = {"x0":0, "zero":0, "x1":1, "ra":1,
                        "x2":2, "sp":2, "x3":3, "gp":3, 
                        "x4":4, "tp":4, "x5":5, "t0":5,
                        "x6":6, "t1":6, "x7":7, "t2":7,
                        "x8":8, "s0":8, "fp":8, 
                        "x9":9, "s1":9, "x10":10, "a0":10, 
                        "x11":11, "a1":11, "x12":12, "a2":12,
                        "x13":13, "a3":13, "x14":14, "a4":14,
                        "x15":15, "a5":15, "x16":16, "a6":16,
                        "x17":17, "a7":17, "x18":18, "s2":18,
                        "x19":19, "s3":19, "x20":20, "s4":20,
                        "x21":21, "s5":21, "x22":22, "s6":22,
                        "x23":23, "s7":23, "x24":24, "s8":24,
                        "x25":25, "s9":25, "x26":26, "s10":26,
                        "x27":26, "s11":27, "x28":28, "t3":28,
                        "x29":29, "t4":29, "x30":30, "t5":30,
                        "x31":31, "at":31
                        }
"""Dictionary that maps register names to their ID numbers (in decimal)"""

def is_register_name(name):
    """Returns True if the provided name is a valid register name or x value."""
    return name in register_name_to_num.keys()

def get_register_bin(name):
    """Returns the binary string version of a register ID given its name."""
    if(name not in register_name_to_num.keys()):
        raise BadRegister("Found unknown register name: \n\t%s\n" % name)
        
    binary_string = format(register_name_to_num[name], "#05b")[2:]
    return "0"*(5-len(binary_string)) + binary_string
    
def is_shift_immediate_inst(inst):
    """Returns true if this is a shift immediate instruction."""
    return inst in ["slli", "srli", "srai"]

def is_core_inst(inst):
    """Returns true if this instruction is in our list of core instructions."""
    return inst in inst_to_types.keys()

def parse_base_offset(operand_string):
    """Takes in the base-offset address field from memory instructions
        returns a tuple including the binary immediate and binary register.

        Assumes the immediate is in decimal.

        e.g. `lw t0, 4(t1)` will lead to this behavior:

            `parse_base_offset("4(t1)") -> ("000000000100", "00110")` """
    #remove the close paren
    operand_string = operand_string.replace(")", "")
    #split on the open to separate the parts
    pieces = operand_string.split("(")
    if(len(pieces) != 2):
        raise BadImmediate("Parsing base-offset address, inappropriate number of elements: \n\t%s\n" % operand_string)

    imm = dec_to_bin(pieces[0])
    rs1 = get_register_bin(pieces[1])
    return (imm, rs1)

def verify_field_sizes(inst_list, inst_type, line_num):
    """Takes in a list where each element is a binary string of one field 
        of an instruction `inst_type` is the Type of the instruction, and 
        `line_num` is the instruction index in the assembled program 
        (`line_num` is only used for error output).

        For example, you could call it this way:

            verify_field_sizes((funct7, rs2, rs1, funct3, rd, opcode), Types.R, 23) 
        
        And it would check that all the various funct7, etc values are an
        appropriate number of bits (well, actually characters since they're
        strings of ones and zeroes).
    """
    raise NotImplementedError

def reverse_string(s):
    """A helper function to reverse strings using list slicing. 
        Just syntactic sugar to help with readability."""
    return s[::-1] 

def is_int(s):
    """Checks if a given string can be an integer or not."""
    try:
        int(s)
    except ValueError:
        return False
    return True

###### Functions to convert between different bases #####

def dec_to_bin(decimal, size=12):
    """Takes a decimal numer (as int or string) and returns the 
        binary representation with number of bits equal to `size`. 
        Uses the two's compliment representation for negative numbers."""
    
    if(type(decimal) == str):
        try:
            decimal = int(decimal)
        except ValueError:
            raise BadImmediate("Failed to parse value as an integer: %s" % (decimal))
    
    if(decimal >= 2**size):
        raise BadImmediate("Not enough bits (%s) to represent the decimal number: %s" % (size, decimal))

    binary_string = bin(((1 << size) - 1) & decimal)
    binary_string = binary_string[2:]
    return "0"*(size-len(binary_string)) + binary_string

def join_inst_fields_bin(inst_list):
    """Takes a list of binary strings and joins them together 
        and grouping into 4 character slices."""
    binary_string = "".join(inst_list)
    binary_string = binary_string.replace(" ", "")
    binary_string = "0"*(32-len(binary_string)) + binary_string
    binary_string = " ".join(binary_string[i:i+4] for i in range(0, 32, 4))
    return binary_string

def bin_to_hex(bin_string):
    """Takes a binary string and converts it into a hex string."""
    #the [2:] here string off the leading '0x' of the hex string
    if(bin_string == None):
        return
    #remove any whitespace in the string
    bin_string = bin_string.replace(" ", "")
    result = hex(int(bin_string, 2))[2:]
    #add in any missing leading zeros
    return "0"*(8-len(result)) + result


##############
#
# Custom Exceptions for Debugging and Niceness 
#
##############

class BadImmediate(Exception):
    """Indicates an immediate is not the right size (in bits) for a given instruction, or some other formatting issue."""
    pass

class BadOperands(Exception):
    """Indicates that the number or type of operands passed to an instruction are incorrect."""
    pass

class BadInstruction(Exception):
    """Indicates that an unknown instruction has been found."""
    pass

class BadRegister(Exception):
    """Indicates that an unknown register has been found."""
    pass

class BadField(Exception):
    """Indicates that the number of bits for an instruction field is incorrect."""
    pass

class BadFormat(Exception):
    """Indicates that the number of fields for a given instruction does not match the format."""
    pass

class BadLabel(Exception):
    """Indicates that a problematic label has been found."""
    pass

##############
#
# Arguments etc.
#
##############
def parse_args():
    """Parses the arguments to the assembler and returns them as a 
        argparse.Namespace object.
        See the python docs for usage.
        """
    parser = argparse.ArgumentParser(description="A parser for 32-bit RISC-V assembly files.")
    parser.add_argument("asm", type=argparse.FileType('r'), help="An asm file containing RISC-V code. \
                        Whitespace will be ignored. Text after a ; is treated as comments. \
                        Labels are identified by a trailing :, they can be on their own line or share a \
                        line with an instruction.")
    parser.add_argument("--out", "-o", type=argparse.FileType('w'), help="The name of the output file that\
                         the assembled machine code will be written to.")
    parser.add_argument("--mode", "-m", choices=["bin","hex"], default="bin", help="The output mode for the\
                         machine file: binary or hexadecimal.")
    parser.add_argument("--verbose", "-v", action="store_true", help="If true then the final output will\
                         include comments listing the RISC-V command that was disassembled on each line, \
                        along with both binary and hex translations.")
    parser.add_argument("--pseudos", "-p", type=argparse.FileType('r'), help="An optional file that defines\
                         pseudoinstructions that this assembler should support.\
                        You should ignore and not use this option unless you talk to an instructor about it.\
                        Pseudoinstruction names and arguments should be listed with a trailing = on one line\
                        then the instructions that define this pseudoinstruction should follow using the argument\
                         names defined on the first line in place of register operands.\
                        EOF or a new pseudoinstruction definition will dileneate the new definitions. \
                        This assumes any register names or numbers (e.g. at, x31, or 31) are constant and should not be\
                         replaced, so dont use register names in the definition. An example:\n\
                        \t double r1, r2 =\
                        \t add r1, r2, r2")
    
    return parser.parse_args()


if __name__== "__main__":
    main(parse_args())
