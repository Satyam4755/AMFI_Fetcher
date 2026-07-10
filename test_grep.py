import re
with open("/Users/smritisoni/.gemini/antigravity-ide/brain/085f44fd-b4bf-4166-b36f-e27dc76b282d/.system_generated/tasks/task-1051.log", "r") as f:
    text = f.read()

# Find the block containing SSD_S-3.xls
idx = text.find("SSD_S-3.xls")
if idx != -1:
    print(text[max(0, idx-500):idx+500])
else:
    print("Not found in task-1051.log")
