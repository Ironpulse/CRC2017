
#include <pybind11/pybind11.h>


namespace pybind11 { namespace detail {
    
    template <> struct type_caster<llvm::StringRef> {
    public:
        
        PYBIND11_TYPE_CASTER(llvm::StringRef, _("llvm::StringRef"));
        
        bool load(handle src, bool) {
            if (!src || !PyUnicode_Check(src.ptr())) {
                return false;
            }
            
            Py_ssize_t size;
            const char * data = PyUnicode_AsUTF8AndSize(src.ptr(), &size);
            if (data == NULL) {
                return false;
            }
            
            // this assumes that the stringref won't be retained after the function call
            value = llvm::StringRef(data, size);
            return true;
        }
        
        static handle cast(const llvm::StringRef &s, return_value_policy, handle) {
            return PyUnicode_FromStringAndSize(s.data(), s.size());
        }
    };
        
        
}} // namespace pybind11::detail
