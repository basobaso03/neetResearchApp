from prompt_toolkit import prompt

while True:
    user_input = prompt('> ', multiline=True)
    print(f"You entered: {user_input}")