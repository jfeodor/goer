import goer

my_other_job = goer.shell(
    "echo other job",
    "sleep 0.5",
    "echo other job done",
)

sources = goer.glob("./source-glob-*.txt")

my_job = goer.shell(
    "echo my job",
    "sleep 0.5",
    "echo my job done",
    "cat source-glob-*.txt > dst-glob.txt",
    depends_on=[my_other_job, sources],
    targets=["dst-glob.txt"],
)

my_third_job = goer.shell(
    "sleep 1",
    "echo third job",
    "sleep 1",
    "echo third job done",
    "echo putting stuff in file > dst-file.txt",
    depends_on=[my_other_job],
    targets=["dst-file.txt"],
)


my_root_job = goer.shell(depends_on=[my_job, my_third_job, my_other_job])
