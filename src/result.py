from typing import Callable, TypeVar, TypeGuard, Awaitable

U = TypeVar('U')

class Result[T]:
    _value: T | None
    _error: BaseException | None

    def __init__(self, value: T | None, error: BaseException | None):
        self._value = value
        self._error = error
    
    def unwrap(self) -> T:
        if self._error is not None or self._value is None:
            if isinstance(self._error, BaseException):
                raise self._error
            else:
                raise Exception(self._error)
        return self._value

    def unwrap_err(self) -> BaseException:
        if self._error is None:
            raise Exception("Result is ok")
        return self._error
    
    def unwrap_or(self, default: T) -> T:
        if self._error is not None or self._value is None:
            return default
        return self._value

    def map_ok(self, func: Callable[[T], U]) -> "Result[U]":
        if self._error is not None or self._value is None:
            return Result(None, self._error)
        return Result(func(self._value), self._error)

    @staticmethod
    def resultify(func: Callable[..., T]) -> "Callable[..., Result[T]]":
        def wrapper(*args, **kwargs) -> Result[T]:
            try:
                return Result(func(*args, **kwargs), None)
            except Exception as e:
                return Result(None, e)
        return wrapper

    @staticmethod
    def resultify_async(func: Callable[..., Awaitable[T]]) -> "Callable[..., Awaitable[Result[T]]]":
        async def wrapper(*args, **kwargs) -> Result[T]:
            try:
                result = await func(*args, **kwargs)
                return Result(result, None)
            except Exception as e:
                return Result(None, e)
        return wrapper

# External TypeGuard functions that actually work
def is_ok[T](res: Result[T]) -> TypeGuard[Result[T]]:
    return res._error is None and res._value is not None

def is_err[T](res: Result[T]) -> TypeGuard[Result[T]]:
    return res._error is not None and res._value is None

def Ok[T](value: T) -> Result[T]:
    return Result(value, None)

def Err[T](error: BaseException) -> Result[T]:
    return Result(None, error)