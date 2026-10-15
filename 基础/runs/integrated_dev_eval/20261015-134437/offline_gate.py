"""检查异常或未明确通过时，绝不调用下一步；本轮不启动任何进程。"""
def after_offline_success(check_step,next_step):
    result=check_step()
    if not isinstance(result,dict) or result.get('returncode')!=0 or result.get('passed') is not True:
        raise RuntimeError('离线检查未明确通过，禁止启动运行器')
    return next_step()
