import asyncio

from foodlog.queueing import REJECT_FULL, REJECT_USER_LIMIT, Job, JobQueue


def job(user, n=0):
    return Job(user, f"m{n}", f"a{n}")


def test_one_at_a_time_in_arrival_order():
    async def main():
        active = peak = 0
        done = []

        async def handler(j):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            done.append(j.message)
            active -= 1

        q = JobQueue(handler, max_size=20, per_user_max=10)
        q.start()
        for i in range(6):
            assert q.put(job(i, i)) is None
        await q._queue.join()
        await q.stop()
        return peak, done

    peak, done = asyncio.run(main())
    assert peak == 1
    assert done == [f"m{i}" for i in range(6)]


def test_limits():
    async def main():
        gate = asyncio.Event()

        async def handler(j):
            await gate.wait()

        q = JobQueue(handler, max_size=3, per_user_max=2)
        q.start()
        assert q.put(job(1, 0)) is None
        await asyncio.sleep(0)  # 讓工人把第一張拿去處理
        assert q.put(job(1, 1)) is None
        assert q.put(job(1, 2)) == REJECT_USER_LIMIT
        assert q.put(job(2, 3)) is None
        assert q.put(job(3, 4)) is None
        assert q.put(job(4, 5)) == REJECT_FULL
        gate.set()
        await q._queue.join()
        assert q.put(job(1, 6)) is None, "處理完之後名額要還回來"
        await q.stop()

    asyncio.run(main())


def test_a_crashing_job_does_not_kill_the_worker():
    async def main():
        seen = []

        async def handler(j):
            if j.message == "boom":
                raise RuntimeError("boom")
            seen.append(j.message)

        q = JobQueue(handler, max_size=10, per_user_max=10)
        q.start()
        for i, m in enumerate(["a", "boom", "b"]):
            q.put(Job(i, m, None))
        await q._queue.join()
        await q.stop()
        return seen

    assert asyncio.run(main()) == ["a", "b"]
