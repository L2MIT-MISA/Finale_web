import express from "express";
import cors from "cors";
import pool, { supabase } from "./db.js";

const app = express();
const PORT = 3001;

app.use(cors());
app.use(express.json());

app.get("/api/statistics", async (req, res) => {
  try {
    // Sites télécom actifs
    const sitesResult = await pool.query(`
      SELECT COUNT(DISTINCT code_site) AS sites_actifs
      FROM infrastructure.pylone
      WHERE tech_2g = true
         OR tech_3g = true
         OR tech_4g = true
         OR tech_5g = true;
    `);

    // Utilisateurs Connectéo
    const { data: totalUsers, error: usersError } =
      await supabase.rpc("get_total_users");

    if (usersError) {
      throw usersError;
    }

    res.json({
      activeTelecomSites: Number(sitesResult.rows[0].sites_actifs),
      totalUsers: Number(totalUsers),
    });
  } catch (error) {
    console.error("Database error:", error);

    res.status(500).json({
      error: "Unable to retrieve statistics",
    });
  }
});

app.listen(PORT, () => {
  console.log(`Backend running on http://localhost:${PORT}`);
});