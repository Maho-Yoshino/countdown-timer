CREATE TABLE classes {
	id INTEGER PRIMARY KEY,
	name TEXT,
	room TEXT,
	teacher TEXT,
	is_temporary INTEGER NOT NULL DEFAULT 0 CHECK (is_temporary IN (0, 1)),

	CHECK (
		is_temporary = 1 OR (
			name IS NOT NULL AND
			room IS NOT NULL AND
			teacher IS NOT NULL
		)
	)
};

CREATE TABLE class_times {
	day INTEGER NOT NULL,
	classNum INTEGER NOT NULL,
	start_time TEXT NOT NULL,
	end_time TEXT NOT NULL,

	PRIMARY KEY (day, classNum)
}

-- Regular schedule
CREATE TABLE schedule {
	day INTEGER NOT NULL,
	classNum INTEGER NOT NULL,
	classID INTEGER REFERENCES classes(id),

	PRIMARY KEY (day, classNum),
	FOREIGN KEY (day, classNum) REFERENCES class_times(day, classNum)
};

-- Temporary schedule changes (substitute, room change due to renovations, etc.)
CREATE TABLE schedule_overrides {
	date TEXT NOT NULL,
	classNum INTEGER NOT NULL,
	classID INTEGER REFERENCES classes(id),

	PRIMARY KEY (date, classNum)
}

