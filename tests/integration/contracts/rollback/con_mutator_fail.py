target_nested = ForeignHash(foreign_contract="con_mutable_map", foreign_name="nested")

@export
def mutate_then_fail_in_callee(key: str, target_contract: str):
    t = importlib.import_module(target_contract)
    d = t.nested[key]
    d["count"] = d.get("count", 0) + 1
    d["items"].append(123)
    assert False, "Failure in callee after mutation"


