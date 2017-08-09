
namespace pybind11 {

    // normal functions
    template <typename Return, typename... Args>
    std::function<Return(Args...)> release_gil(Return (*f)(Args ...) PYBIND11_NOEXCEPT_SPECIFIER) {
        return [f](Args... args) -> Return {
            gil_scoped_release r;
            return f(args...);
        };
    }
    
    // member functions (non-const)
    template <typename Return, typename Class, typename... Args>
    std::function<Return(Class*, Args...)> release_gil(Return (Class::*f)(Args ...) PYBIND11_NOEXCEPT_SPECIFIER) {
        return [f](Class *c, Args... args) -> Return {
            gil_scoped_release r;
            return (c->*f)(args...);
        };
    }
    
    // member functions (const)
    template <typename Return, typename Class, typename... Args>
    std::function<Return(Class*, Args...)> release_gil(Return (Class::*f)(Args ...) const PYBIND11_NOEXCEPT_SPECIFIER) {
        return [f](const Class *c, Args... args) -> Return {
            gil_scoped_release r;
            return (c->*f)(args...);
        };
    }
    
} // namespace pybind11