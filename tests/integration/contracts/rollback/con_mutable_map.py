nested = Hash()
aliased = Hash(default_value={"count": 0, "items": []})

@export
def init_key(key: str):
    assert ":" not in key and "." not in key, "Illegal key"
    nested[key] = {"count": 1, "items": [1]}

@export
def mutate_in_place_and_fail(key: str):
    d = nested[key]
    d["count"] = d.get("count", 0) + 1
    d["items"].append(2)
    assert False, "Forced failure after in-place mutation"

@export
def read(key: str):
    return nested[key]

@export
def init_nested(key: str):
    assert ":" not in key and "." not in key, "Illegal key"
    nested[key] = {"child": {"x": 1}, "items": [{"v": 1}]}

@export
def mutate_nested_and_fail(key: str):
    d = nested[key]
    d["child"]["x"] = d["child"].get("x", 0) + 1
    d["items"][0]["v"] = 2
    assert False, "Forced failure after deep in-place mutation"

@export
def mutate_then_reassign_and_fail(key: str):
    d = nested[key]
    d["count"] = d.get("count", 0) + 1
    nested[key] = d
    assert False, "Forced failure after reassign"

@export
def cross_mutate_then_fail(key: str, mutator: str = "con_mutator"):
    m = importlib.import_module(mutator)
    m.mutate_target(key=key, target_contract=str(ctx.this))
    assert False, "Forced failure after cross-contract mutation"

@export
def alias_set(key: str):
    assert ":" not in key and "." not in key, "Illegal key"
    v = aliased[key]
    aliased[key] = {"count": v.get("count", 0), "items": list(v.get("items", []))}

@export
def alias_mutate_and_fail(key: str):
    d = aliased[key]
    d["count"] = d.get("count", 0) + 1
    d["items"].append(7)
    assert False, "Forced failure after alias mutate"

@export
def type_error_after_mutation(key: str):
    d = nested[key]
    d["count"] = d["count"] + 1
    oops = 1 + "x"


