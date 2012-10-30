import fill
import array
a = array.array('I')
a.append(1)
a.append(1)
a.append(3)
a.append(2)
a.append(2)
a.append(2)
a.append(2)
a.append(2)
a.append(2)
a.append(2)
a.append(2)
a.append(2)
print "before", a
b = fill.fill(a,2,2,3,3,4278190080)
print "after", b

print "after 2", array.array('I', b)
