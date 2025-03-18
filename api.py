from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from db import get_db_connection

app = FastAPI()

# Allow CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with frontend URL for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Production Scheduling API"}

# ✅ Fetch all unscheduled batches
@app.get("/schedule")
def get_schedule():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM production_plan WHERE schedule = FALSE")
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Fetch a specific batch by ID
@app.get("/schedule/{batch_id}")
def get_batch(batch_id: int):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM production_plan WHERE id = %s", (batch_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            return row
        raise HTTPException(status_code=404, detail="Batch not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Update batch scheduling status
@app.put("/schedule/{batch_id}")
def update_schedule(batch_id: int, scheduled: bool):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE production_plan SET schedule = %s WHERE id = %s RETURNING *",
            (scheduled, batch_id),
        )
        updated_row = cur.fetchone()
        conn.commit()
        conn.close()
        if updated_row:
            return {"message": "Schedule updated", "batch": updated_row}
        raise HTTPException(status_code=404, detail="Batch not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Delete a batch from the schedule
@app.delete("/schedule/{batch_id}")
def delete_batch(batch_id: int):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM production_plan WHERE id = %s RETURNING *", (batch_id,))
        deleted_row = cur.fetchone()
        conn.commit()
        conn.close()
        if deleted_row:
            return {"message": "Batch deleted", "batch": deleted_row}
        raise HTTPException(status_code=404, detail="Batch not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

