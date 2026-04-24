file_path = "ranker_node/Search.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace("json.dumps(payload)", "json.dumps(payload, default=str)")

with open(file_path, "w") as f:
    f.write(content)
