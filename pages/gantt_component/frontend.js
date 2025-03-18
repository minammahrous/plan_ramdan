import React, { useEffect, useState } from "react";
import { Streamlit, withStreamlitConnection } from "streamlit-component-lib";
import ScheduleTimelineCalendar from "react-gantt-schedule-timeline-calendar";

const GanttChart = ({ args }) => {
    const [tasks, setTasks] = useState(JSON.parse(args.tasks));

    useEffect(() => {
        Streamlit.setFrameHeight();
    }, []);

    const handleTaskUpdate = (task) => {
        const updatedTasks = tasks.map(t => t.id === task.id ? task : t);
        setTasks(updatedTasks);
        Streamlit.setComponentValue(updatedTasks);
    };

    return (
        <ScheduleTimelineCalendar
            items={tasks}
            onChange={handleTaskUpdate}
            startField="start"
            endField="end"
            groupField="machine"
            draggable
            resizable
            editable
        />
    );
};

export default withStreamlitConnection(GanttChart);

