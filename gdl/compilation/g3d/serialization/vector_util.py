from math import cos, sin

def vertex_cross_product(v0, v1, v2):
    return cross_product(line_from_verts(v0, v1),
                         line_from_verts(v0, v2))


def cross_product(ray_a, ray_b):
    return ((ray_a[1]*ray_b[2] - ray_a[2]*ray_b[1],
             ray_a[2]*ray_b[0] - ray_a[0]*ray_b[2],
             ray_a[0]*ray_b[1] - ray_a[1]*ray_b[0]))


def euler_to_quaternion(y, p, r):
    '''Angles are expected to be in radians.'''
    c0, c1, c2 = cos(y / 2), cos(p / 2), cos(r / 2)
    s0, s1, s2 = sin(y / 2), sin(p / 2), sin(r / 2)
    return (s0*s1*c2 + c0*c1*s2, s0*c1*c2 + c0*s1*s2,
            c0*s1*c2 - s0*c1*s2, c0*c1*c2 - s0*s1*s2)


def quaternion_to_matrix(i, j, k, w):
    return Matrix([
        (2*(0.5 - j*j - k*k),   2*(i*j + k*w),         2*(i*k - j*w)),
        (2*(i*j - k*w),         2*(0.5 - k*k - i*i),   2*(j*k + i*w)),
        (2*(i*k + j*w),         2*(j*k - i*w),         2*(0.5 - i*i - j*j)),
    ])


class FixedLengthList(list):
    __slots__ = ()
    def append(self, val): raise NotImplementedError
    def extend(self, vals): raise NotImplementedError
    def insert(self, index, val): raise NotImplementedError
    def pop(self): raise NotImplementedError
    def __delitem__(self): raise NotImplementedError
    def __setitem__(self, index, val):
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self))
            if start > stop:
                start, stop = stop, start
            if start == stop:
                return
            elif step < 0:
                step = -step

            slice_size = (stop - start) // step

            if slice_size != len(val):
                raise ValueError(("attempt to assign sequence of size %s to "
                                  "slice of size %s") % (len(val), slice_size))

        list.__setitem__(self, index, val)


class Vector(list):
    __slots__ = ()
    '''Implements the minimal methods required for messing with matrix rows'''
    def __neg__(self):
        return type(self)(-x for x in self)
    def __add__(self, other):
        new = type(self)(self)
        for i in range(len(other)): new[i] += other[i]
        return new
    def __sub__(self, other):
        new = type(self)(self)
        for i in range(len(other)): new[i] -= other[i]
        return new
    def __mul__(self, other):
        if isinstance(other, type(self)):
            return sum(self[i]*other[i] for i in range(len(self)))
        new = type(self)(self)
        for i in range(len(self)): new[i] *= other
        return new
    def __truediv__(self, other):
        if isinstance(other, type(self)):
            return cross_product(self, other)
        new = type(self)(self)
        for i in range(len(self)): new[i] /= other
        return new
    def __eq__(self, other):
        return are_vectors_equal(self, other)
    def __iadd__(self, other):
        for i in range(len(other)): self[i] += other[i]
        return self
    def __isub__(self, other):
        for i in range(len(other)): self[i] -= other[i]
        return self
    def __imul__(self, other):
        if isinstance(other, type(self)):
            raise NotImplementedError
        for i in range(len(self)): self[i] *= other
        return self
    def __itruediv__(self, other):
        if isinstance(other, type(self)):
            raise NotImplementedError
        for i in range(len(self)): self[i] /= other
        return self

    __radd__ = __add__
    __rsub__ = __sub__
    __rmul__ = __mul__
    __rtruediv__ = __truediv__


class MatrixRow(FixedLengthList, Vector):
    __slots__ = ()


class Matrix(list):
    width = 1
    height = 1

    def __init__(self, matrix=None, width=1, height=1, identity=False):
        if matrix is None:
            self.width = width
            self.height = height
            list.__init__(self, (MatrixRow((0,)*width) for i in range(height)))

            if identity and width <= height:
                # place the identity matrix into the inverse
                for i in range(self.width):
                    self[i][i] = 1.0
            return

        matrix_rows = []
        self.height = max(1, len(matrix))
        self.width = -1
        for row in matrix:
            if not hasattr(row, '__iter__'):
                row = [row]
            self.width = max(self.width, len(row))
            assert self.width and len(row) == self.width
            matrix_rows.append(MatrixRow(row[:]))
        list.__init__(self, matrix_rows)

    def __setitem__(self, index, new_row):
        assert len(new_row) == self.width
        list.__setitem__(self, index, MatrixRow(new_row))

    def __delitem__(self, index):
        self[index][:] = (0,)*self.width

    def __str__(self):
        matrix_str = "Matrix([\n%s])"
        insert_str = ''
        for row in self:
            insert_str += '%s,\n' % (row,)
        return matrix_str % insert_str

    def __neg__(self):
        return Matrix([-row for row in self])

    def __add__(self, other):
        assert isinstance(other, Matrix)
        assert self.width == other.width and self.height == other.height
        new = Matrix(self)
        for i in range(len(other)): new[i] += other[i]
        return new

    def __sub__(self, other):
        assert isinstance(other, Matrix)
        assert self.width == other.width and self.height == other.height
        new = Matrix(self)
        for i in range(len(other)): new[i] -= other[i]
        return new

    def __mul__(self, other):
        assert isinstance(other, (Matrix, int, float))
        if not isinstance(other, Matrix):
            new = Matrix(self)
            for row in new:
                row *= other
            return new

        assert self.width == other.height
        # transpose the matrix so its easier to work with
        new = Matrix(width=other.width, height=self.height)
        other = other.transpose

        # loop over each row in the new matrix
        for i in range(new.height):
            # loop over each column in the new matrix
            for j in range(new.width):
                # set the element equal to the dot product of the matrix rows
                new[i][j] = self[i]*other[j]

        return new

    def __truediv__(self, other):
        assert isinstance(other, (Matrix, int, float))
        if not isinstance(other, Matrix):
            new = Matrix(self)
            for row in new:
                row /= other
            return new
        assert self.width == other.height
        return self * other.inverse

    __repr__ = __str__
    __radd__ = __add__
    __rsub__ = __sub__
    __rmul__ = __mul__
    __rtruediv__ = __truediv__

    def __iadd__(self, other):
        assert isinstance(other, Matrix)
        assert self.width == other.width and self.height == other.height
        for i in range(len(other)): self[i] += other[i]
        return self

    def __isub__(self, other):
        assert isinstance(other, Matrix)
        assert self.width == other.width and self.height == other.height
        for i in range(len(other)): self[i] -= other[i]
        return self

    def __imul__(self, other):
        assert isinstance(other, (Matrix, int, float))
        if not isinstance(other, Matrix):
            for row in self:
                row *= other
            return self

        assert self.width == other.height
        # transpose the matrix so its easier to work with
        new = Matrix(width=other.width, height=self.height)
        other = other.transpose

        # loop over each row in the new matrix
        for i in range(new.height):
            # loop over each column in the new matrix
            for j in range(new.width):
                # set the element equal to the dot product of the matrix rows
                new[i][j] = self[i]*other[j]

        # replace the values in this matrix with those in the new matrix
        self.width = 0
        self.height = new.height
        for i in range(self.height):
            self.width = len(self[i])
            self[i] = new[i]

        return self

    def __itruediv__(self, other):
        assert isinstance(other, (Matrix, int, float))
        if not isinstance(other, Matrix):
            for row in self:
                row /= other
            return self
        self *= other.inverse
        return self

    def to_quaternion(self):
        assert self.width == 3
        assert self.height == 3
        return Quaternion(matrix_to_quaternion(self))

    @property
    def determinant(self):
        assert self.width == self.height, "Non-square matrices do not have determinants."
        if self.width == 2:
            return self[0][0] * self[1][1] - self[0][1] * self[1][0]

        d = 0
        sub_matrix = Matrix(width=self.width - 1, height=self.height - 1)
        for i in range(self.width):
            for j in range(sub_matrix.height):
                for k in range(sub_matrix.width):
                    sub_matrix[j][k] = self[j+1][(i + k + 1) % self.width]
            d += self[0][i] * sub_matrix.determinant

        return d

    @property
    def transpose(self):
        transpose = Matrix(width=self.height, height=self.width)
        for r in range(self.height):
            for c in range(self.width):
                transpose[c][r] = self[r][c]
        return transpose

    @property
    def inverse(self, find_best_inverse=True):
        # cannot invert non-square matrices. check for that
        if self.width != self.height:
            raise MatrixNotInvertable("Cannot invert non-square matrix.")
        elif not self.determinant:
            raise MatrixNotInvertable("Matrix is non-invertible.")

        regular, inverse = self.row_reduce(
            Matrix(width=self.width, height=self.height, identity=True),
            find_best_reduction=find_best_inverse
            )

        return inverse

    def row_reduce(self, other, find_best_reduction=True):
        # cant row-reduce if number of columns is greater than number of rows
        assert self.width <= self.height

        # WIDTH NOTE: We will loop over the width rather than height for
        #     several things here, as we do not care about any rows that
        #     don't intersect the columns at a diagonal. Essentially we're
        #     treating a potentially non-square matrix as square(we're
        #     ignoring the higher numbered rows) by rearranging the rows.

        new_row_order = self.get_row_reduce_order(find_best_reduction)
        if new_row_order is None:
            raise CannotRowReduce(
                "Impossible to rearrange rows to row-reduce:\n%s" % self)

        reduced = Matrix(self)
        orig_other = list(other)
        # rearrange rows so diagonals are all non-zero
        for i in range(len(new_row_order)):
            reduced[i] = self[new_row_order[i]]
            other[i] = orig_other[new_row_order[i]]

        orig_reduced = Matrix(reduced)  # TEMP
        for i in range(self.width):  # read note about looping over width
            # divide both matrices by their diagonal values
            div = reduced[i][i]
            if not div:
                raise CannotRowReduce("Impossible to row-reduce.")

            reduced[i] /= div
            other[i] /= div

            # make copies of the rows that we can multiply for subtraction
            reduced_diff = MatrixRow(reduced[i])
            other_diff = MatrixRow(other[i])

            # loop over the rows NOT intersecting the column at the diagonal
            for j in range(self.width):
                if i == j:
                    continue
                # get the value that needs to be subtracted from
                # where this row intersects the current column
                mul = reduced[j][i]

                # subtract the difference row from each of the
                # rows above it to set everything in the column
                # above an below the diagonal intersection to 0
                reduced[j] -= reduced_diff*mul
                other[j] -= other_diff*mul

        return reduced, other

    def get_row_reduce_order(self, find_best_reduction=True):
        nonzero_diag_row_indices = list(set() for i in range(self.width))
        valid_row_orders = {}

        # determine which rows have a nonzero value on each diagonal
        for i in range(self.height):
            for j in range(self.width):
                if self[i][j]:
                    nonzero_diag_row_indices[j].add(i)

        self._get_valid_diagonal_row_orders(
            nonzero_diag_row_indices, valid_row_orders, find_best_reduction)

        # get the highest weighted row order
        test_matrix = Matrix(width=self.width, height=self.width)
        for weight in reversed(sorted(valid_row_orders)):
            for row_order in valid_row_orders[weight]:
                for i in range(len(row_order)):
                    test_matrix[i][:] = self[row_order[i]]

                # make sure the determinant of the matrix made from the
                # row order isn't zero. if it is, the matrix isnt solvable
                if test_matrix.determinant:
                    return row_order

        return None

    def _get_valid_diagonal_row_orders(self, row_indices, row_orders,
                                       choose_best=True, row_order=(),
                                       curr_column=0):
        row_order = list(row_order)
        column_count = len(row_indices)
        if not row_order:
            row_order = [None] * column_count

        # loop over each row with a non-zero value on this diagonal
        for i in row_indices[curr_column]:
            if row_orders and not choose_best:
                # found a valid row arrangement, don't keep checking
                break
            elif i in row_order:
                continue

            row_order[curr_column] = i
            if curr_column + 1 == column_count:
                weight = 1.0
                for j in range(len(row_order)):
                    weight *= abs(self[row_order[j]][j])

                # freeze this row order in place
                row_orders.setdefault(weight, []).append(tuple(row_order))
            else:
                # check the rest of the rows
                self._get_valid_diagonal_row_orders(
                    row_indices, row_orders, choose_best,
                    row_order, curr_column + 1)