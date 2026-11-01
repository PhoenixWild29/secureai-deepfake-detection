from secureai_shared.limits import RedisRateLimiter


def test_redis_limiter_sets_expiry_in_the_same_script_call() -> None:
    seen: dict[str, object] = {}

    class Redis:
        def register_script(self, script: str):
            seen["script"] = script

            def run(keys, args):
                seen["keys"] = keys
                seen["args"] = args
                return 2

            return run

    limiter = RedisRateLimiter(
        "redis://unused",
        {"jobs": 1},
        60,
        prefix="secureai:jobs:rl",
        client=Redis(),
    )
    assert limiter.allow("jobs", "user_dev") is False
    script = str(seen["script"])
    assert "INCR" in script
    assert "EXPIRE" in script
    assert seen["keys"] == ["secureai:jobs:rl:jobs:user_dev"]
    assert seen["args"] == [60]


def test_redis_limiter_allows_the_first_hit() -> None:
    class Redis:
        def register_script(self, script: str):
            del script

            def run(keys, args):
                del keys, args
                return 1

            return run

    limiter = RedisRateLimiter(
        "redis://unused",
        {"uploads": 5},
        30,
        prefix="rl",
        client=Redis(),
    )
    assert limiter.allow("uploads", "user_dev") is True
    assert limiter.allow("disabled", "user_dev") is True
