from decimal import Decimal


class Expression:
    _str_repr = "{x}"
    _static_vars = dict()
    _dynamic_vars = ['x']
    _var_nicknames = dict()
    _eval_vars = []
    _special_vars = dict()

    def __init__(self, **statics):
        self._static_vars.update(statics)
        self._dynamic_var_names = dict()
        for e in self._dynamic_vars:
            if e in self._var_nicknames:
                self._dynamic_var_names[e] = self._var_nicknames[e]
            else:
                self._dynamic_var_names[e] = e
        self.post_init()

    def post_init(self):
        pass

    def execute(self, **dynamic):
        for var in self._dynamic_vars:
            if var not in dynamic:
                raise ValueError(f"No such variable {var}")
        return self._f(**dynamic, **self._static_vars)

    def _f(self, x, **kw):
        return x

    def compile(self, no_edit=False, include_static=True, **kwargs):
        if not no_edit:
            for e in kwargs:
                if str(kwargs[e]).startswith('-'):
                    kwargs[e] = f"({str(kwargs[e])})"
        if include_static:
            kwargs.update(self._static_vars)
        result = self._str_repr.format(**kwargs)

        return result

    def get_unified(self):
        return self.compile(**self._dynamic_var_names,
                            **self._special_vars)

    def get_local(self, **dynamic):
        return self.compile(**dynamic,
                            **self._special_vars) +\
               f" = {self.execute(**dynamic)}"

    def __str__(self):
        return self._str_repr


class MainExpr(Expression):
    _str_repr = "{a}*{x}^3 + {b}*{a}*{x}^2 - {a}*{x} - {b}*{a}"

    def _f(self, x: Decimal, a: Decimal, b: Decimal, **kwargs):
        return a*x**3 + b*a*x**2 - a*x - b*a


class MainExprDerivative(Expression):
    _str_repr = "3*{a}*{x}^2 + 2*{b}*{a}*{x} - {a}"

    def _f(self, x: Decimal, a: Decimal, b: Decimal, **kwargs):
        return 3*a*x**2 + 2*b*a*x - a


class SolveMethod:
    _method_name = "basic method"
    _check_repr = "\t(check f({x}+{epsilon})*f({x}-{epsilon}) < 0, {check_result})\n"

    def __init__(self, expr: Expression,
                 lbound: Decimal,
                 rbound: Decimal,
                 accuracy=4,
                 suppres_info=False,
                 **kwargs):
        self.suppres_info = suppres_info
        self.expr = expr
        self.lbound = lbound
        self.rbound = rbound
        self.x = Decimal("0")
        self.extra = kwargs
        from decimal import getcontext
        getcontext().prec = accuracy+2
        self.accuracy = accuracy
        self.epsilon = Decimal("1")/10**accuracy
        self._stop_expr = self.StopExpression()
        self._step_expr = self.StepExpression()
        self.post_init(**kwargs)

    def post_init(self, **kwargs):
        pass

    def show_cache_prepare(self):
        pass

    def step(self):
        pass

    def show_step_prepare(self):
        pass

    def show_step(self, **kwargs):
        if self.suppres_info:
            return
        print(f"x = {self._step_expr.get_unified()} = {self._step_expr.get_local(**kwargs)}")

    def show_check(self, result, **check_fargs):
        if self.suppres_info:
            return
        print(f"\t\t{{ check {self._stop_expr.get_unified()} = {self._stop_expr.compile(**check_fargs)} = {result} }}\n")

    def stop_needed(self) -> bool:
        params = dict(
            f_x1=self.expr.execute(x=self.x + self.epsilon),
            f_x2=self.expr.execute(x=self.x - self.epsilon)
        )
        result = self._stop_expr.execute(**params) < Decimal("0")
        self.show_check(result, **params)
        return result

    @staticmethod
    def show_current_evaluation(expr: Expression, name: str = "f(x)", **kwargs):
        print(f"\t{name} = {expr.get_local(**kwargs)}")\

    @staticmethod
    def show_first_evaluation(expr: Expression, name: str = "f(x)", **kwargs):
        print(f"\t{name} = {expr.get_unified()} = {expr.get_local(**kwargs)}")

    def run(self):
        if not self.suppres_info:
            print(f"Attempt to find root in [{self.lbound}, {self.rbound}],\n"
                  f"Use '{self._method_name}':")
        i = 1
        if not self.suppres_info:
            self.show_cache_prepare()
        while i == 1 or not self.stop_needed():
            if not self.suppres_info:
                print(f"Step #{i}:")
                self.show_step_prepare()
            self.step()
            i += 1
        return self.x
        
    class StepExpression(Expression):
        pass

    class StopExpression(Expression):
        _str_repr = "{f_x1}*{f_x2} < 0"
        _dynamic_vars = ['f_x1', 'f_x2']
        _static_vars = dict()
        _var_nicknames = {
            'f_x1': "f(x+e)",
            'f_x2': "f(x-e)",
        }

        def _f(self, f_x1, f_x2, **kwargs):
            return f_x1 * f_x2


class TangentMethod(SolveMethod):
    _method_name = "Метод касательных"

    def post_init(self, **kwargs):
        self.x = self.rbound
        self.d_expr: Expression = kwargs['d_expr']

    def show_step_prepare(self, **kwargs):
        SolveMethod.show_current_evaluation(self.expr, x=self.x)
        SolveMethod.show_current_evaluation(self.d_expr, x=self.x, name="f'(x)")

    def step(self):
        params = dict(
            f_x=self.expr.execute(x=self.x),
            df_x=self.d_expr.execute(x=self.x),
            x=self.x
        )
        self.show_step(**params)
        self.x = self._step_expr.execute(**params)

    class StepExpression(Expression):
        _str_repr = "{x} - {f_x}/{df_x}"
        _dynamic_vars = ['x', 'f_x', 'df_x']
        _static_vars = dict()
        _var_nicknames = {
            'df_x': "f'(x)",
            'f_x': "f(x)",
        }

        def _f(self, df_x, f_x, x, **kwargs):
            return x - f_x/df_x


class SecantMethod(SolveMethod):
    _method_name = "Метод секущих"

    def post_init(self, **kwargs):
        self.x = self.lbound

    def show_cache_prepare(self):
        print("Prepare:")
        print("x = a =", self.lbound)
        SolveMethod.show_current_evaluation(self.expr, x=self.rbound, name="f(b)")

    def show_method_starts(self):
        self.show_repr(self._method_starts_repr,
                       f_x=self.expr.execute(x=self.x),
                       f_b=self.expr.execute(x=self.rbound),
                       )

    def show_step_prepare(self, **kwargs):
        SolveMethod.show_current_evaluation(self.expr, x=self.x)

    def step(self):
        params = dict(
            f_x=self.expr.execute(x=self.x),
            f_b=self.expr.execute(x=self.rbound),
            x=self.x,
            b=self.rbound,
        )
        self.show_step(**params)
        self.x = self._step_expr.execute(**params)

    class StepExpression(Expression):
        _str_repr = "{x} - ({f_x}*({x}-{b}))/({f_x}-{f_b})"
        _dynamic_vars = ['x', 'f_x', 'f_b', 'b']
        _static_vars = dict()
        _var_nicknames = {
            'f_x': "f(x)",
            'f_b': "f(b)",
        }

        def _f(self, f_x, f_b, x, b, **kwargs):
            return x - (f_x*(x-b))/(f_x-f_b)


class SimpleIterationsMethod(SolveMethod):
    _method_name = "Метод простых итераций"

    def post_init(self, **kwargs):
        self.x = (self.lbound+self.rbound)/Decimal("2")
        self.d_expr: Expression = kwargs['d_expr']
        self.k_expr = self.kExpr()
        self.k = self.k_expr.execute(x=self.x, df_x=self.d_expr.execute(x=self.x))

    def show_cache_prepare(self):
        print("Prepare:")
        SolveMethod.show_first_evaluation(self.StartXExpr(), 'x',
                                            a=self.lbound,
                                            b=self.rbound)
        SolveMethod.show_current_evaluation(self.d_expr, x=self.x, name="f'(x)")
        SolveMethod.show_first_evaluation(self.k_expr, x=self.x, name="k",
                                                df_x=self.d_expr.execute(x=self.x))

    def show_step_prepare(self, **kwargs):
        SolveMethod.show_current_evaluation(self.expr, x=self.x)

    def step(self):
        params = dict(
            f_x=self.expr.execute(x=self.x),
            x=self.x,
            k=self.k,
        )
        self.show_step(**params)
        self.x = self._step_expr.execute(**params)

    class StartXExpr(Expression):
        _str_repr = "({a}+{b})/2"
        _dynamic_vars = ['a', 'b']
        _static_vars = dict()

        def _f(self, a, b, **kwargs):
            return (a+b)/Decimal('2')

    class StepExpression(Expression):
        _str_repr = "{x} - {k}*{f_x}"
        _dynamic_vars = ['x', 'f_x', 'k']
        _static_vars = dict()
        _var_nicknames = {
            'f_x': "f(x)",
        }

        def _f(self, f_x, x, k, **kwargs):
            return x - k*f_x

    class kExpr(Expression):
        _str_repr = "1/{df_x}"
        _dynamic_vars = ['x', 'df_x']
        _static_vars = dict()
        _var_nicknames = {'df_x': "f'(x)"}

        def _f(self, df_x, **kwargs):
            return Decimal("1") / df_x


def main():
    a = input("Введите a: ")
    b = input("Введите b: ")

    expr = MainExpr(a=Decimal(a), b=Decimal(b))
    d_expr = MainExprDerivative(a=Decimal(a), b=Decimal(b))
    b = Decimal(b)

    print("f(x):", expr.get_unified())
    print("f'(x):", d_expr.get_unified())

    extr1 = Decimal(input("Введите extr1: "))
    extr2 = Decimal(input("Введите extr2: "))
    
    methods = [
        (TangentMethod, (extr2, Decimal("2"))),
        (SecantMethod, (-b+Decimal("0.5"), Decimal("-0.5"))),
        (SimpleIterationsMethod, (-b-Decimal("1"), extr1)),
    ]

    for (method, bounds) in methods:
        print("\n\t\t\t---\n")
        solver = method(expr=expr,
                        lbound=bounds[0],
                        rbound=bounds[1],
                        d_expr=d_expr,
                        accuracy=3,
                        )
        x = solver.run()
        print(f"Root is {x}, proof: {expr.execute(x=x)}")


if __name__ == '__main__':
    main()
