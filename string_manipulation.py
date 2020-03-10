# # Number or not, returns true or false
# "Forest".isnumeric()
# "12344".isnumeric()
# # convert to number
# int("12345") + int("54321")
# # join to concatanate
# " ".join(["This", "is","a","sentence"])
#
# "...".join(["This", "is","a","sentence"])
# # split a string by eliminating white space
#
# print("This is another example".split())
# Formating
# def formated_string(Name):
#     Number = len(Name) * 3
#     print("Hey {}, your lucky number is {}".format(Name, Number))
#
# formated_string("Muntasir")
#
# # Another way
# def formated_string(Name):
#     Number = len(Name) * 3
#     print("Hey {name}, your lucky number is {number}".format(name=Name, number=(Number)*3))
#
# formated_string("Muntasir")

def to_celsius(t):
    return (x-32)*5/9

for x in range(0,101,10):
    print("{:>3} F | {:>6.2f} C".format(x, to_celsius(x)))