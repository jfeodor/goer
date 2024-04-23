import goer
from goer.rules import FileRule, SourceGlobRule

my_other_job = goer.job(
    "echo other job",
    "sleep 0.5",
    "echo other job done",
)

my_job = goer.job(
    "echo my job",
    "sleep 0.5",
    "echo my job done",
    "cat source-glob-*.txt > dst-glob.txt",
    depends_on=[my_other_job],
    rules=[SourceGlobRule("source-glob-*.txt", "dst-glob.txt")],
)

my_third_job = goer.job(
    "sleep 1",
    "echo third job",
    "sleep 1",
    "echo third job done",
    "echo putting stuff in file > dst-file.txt",
    rules=[FileRule("./file.txt", "./dst-file.txt")],
    depends_on=[],
)


my_root_job = goer.job(depends_on=[my_job, my_third_job])
