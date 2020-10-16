from decimal import Decimal


class Expression:
    _str_repr = "{x} = {ans}"

    def __init__(self, **kw):
        self.args = kw
        self.post_init()

    def post_init(self):
        pass

    def f(self, x, **kwargs):
        return x

    def __str__(self):
        return self._str_repr


class MainExpr(Expression):
    _str_repr = "{a}*{{x}}^3 + {b}*{a}*{{x}}^2 - {a}*{{x}} - {b}*{a} = {{ans}}"

    def post_init(self):
        self.a = Decimal(self.args['a'])
        self.b = Decimal(self.args['b'])
        self._str_repr = self._str_repr.format(a=self.args['a'],
                                               b=self.args['b'],
                                               x="x", ans="ans")

    def f(self, x, **kwargs):
        return self.a*x**3 + self.b*self.a*x**2 - self.a*x - self.b*self.a


class MainExprDerivative(MainExpr):
    _str_repr = "3*{a}*{{x}}^2 + 2*{b}*{a}*{{x}} - {a} = {{ans}}"

    def f(self, x, **kwargs):
        return 3*self.a*x**2 + 2*self.b*self.a*x - self.a


class SolveMethod:
    _method_name = "basic method"
    _method_starts_repr = "x = g({x})"
    _method_clear_repr = "x = g(x)"
    _method_ends_repr = " = {x}\n"
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
        self.post_init(**kwargs)

    def post_init(self, **kwargs):
        pass

    def step(self):
        pass

    def show_repr(self, repr, **extra):
        if self.suppres_info:
            return
        print(repr.format(
            x=self.x,
            lbound=self.lbound,
            rbound=self.rbound,
            epsilon=self.epsilon,
            **extra
        ), end='')

    def show_method_starts(self):
        self.show_repr(self._method_starts_repr)

    def show_method_ends(self):
        self.show_repr(self._method_ends_repr)

    def show_check(self):
        self.show_repr(self._check_repr, check_result=self.stop_needed())

    def stop_needed(self) -> bool:
        return self.expr.f(self.x+self.epsilon) * \
               self.expr.f(self.x-self.epsilon) < Decimal("0")

    def run(self):
        if not self.suppres_info:
            print(f"Attempt to find root in [{self.lbound}, {self.rbound}],\n"
                  f"Use '{self._method_name}':")

        i = 1
        while not self.stop_needed():
            if not self.suppres_info:
                print(f"Step #{i}:", self._method_clear_repr)
            self.show_method_starts()
            self.step()
            self.show_method_ends()
            self.show_check()
            i += 1
        return self.x

    def print_current_step(self):
        print(str(self.expr).format(x=self.x,
                                    ans=self.expr.f(self.x),
                                    **self.extra))


class BinarySearchMethod(SolveMethod):
    _method_name = "Метод половинных делений"
    _method_starts_repr = "x = ({lbound}+{rbound})/2"
    _method_clear_repr = "x = (a+b)/2"
    _method_ends_repr = " = {x} => new bounds [{lbound}, {rbound}]\n"

    def step(self):
        self.x = (self.lbound+self.rbound)/2
        if (self.expr.f(self.x) > 0) == (self.expr.f(self.lbound) > 0):
            self.lbound = self.x
        else:
            self.rbound = self.x


class TangentMethod(SolveMethod):
    _method_name = "Метод касательных"
    _method_starts_repr = "x = {x} - {f_x} / {df_x}"
    _method_clear_repr = "x = x - f(x)/f'(x)"
    _method_ends_repr = " = {x}\n"

    def post_init(self, **kwargs):
        self.x = self.rbound
        self.d_expr: Expression = kwargs['d_expr']

    def show_method_starts(self):
        self.show_repr(self._method_starts_repr,
                       f_x=self.expr.f(self.x),
                       df_x=self.d_expr.f(self.x),
                       )

    def step(self):
        self.x -= self.expr.f(self.x) / self.d_expr.f(self.x)


class SecantMethod(SolveMethod):
    _method_name = "Метод секущих"
    _method_starts_repr = "x = {x} - {f_x}/({f_x} - {f_b})*({x}-{rbound})"
    _method_clear_repr = "x = x - f(x)/(f(x)-f(b)) * (x-b)"
    _method_ends_repr = " = {x}\n"

    def post_init(self, **kwargs):
        self.x = self.lbound

    def show_method_starts(self):
        self.show_repr(self._method_starts_repr,
                       f_x=self.expr.f(self.x),
                       f_b=self.expr.f(self.rbound),
                       )

    def step(self):
        self.x -= self.expr.f(self.x) /\
                  (self.expr.f(self.x) - self.expr.f(self.rbound)) *\
                  (self.x-self.rbound)


class SimpleIterationsMethod(SolveMethod):
    _method_name = "Метод простых итераций"
    _method_starts_repr = "x = {x} - {k}*{f_x}"
    _method_clear_repr = "x = x - k*f(x)"
    _method_ends_repr = " = {x}\n"

    def post_init(self, **kwargs):
        self.x = (self.lbound+self.rbound)/Decimal("2")
        df: Expression = kwargs['d_expr']
        self.k = Decimal("1")/df.f(self.x)

    def show_method_starts(self):
        self.show_repr(self._method_starts_repr,
                       f_x=self.expr.f(self.x),
                       k=self.k,
                       )

    def step(self):
        self.x -= self.k*self.expr.f(self.x)


def main():
    a = "1"
    b = "4.74"
    extr1 = Decimal("-3.262")
    extr2 = Decimal("0.102")
    expr = MainExpr(a=a, b=b)
    d_expr = MainExprDerivative(a=a, b=b)
    b = Decimal(b)
    methods = [
        #BinarySearchMethod,
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
        print(f"Root is {x}, proof: {expr.f(x)}")


if __name__ == '__main__':
    main()
