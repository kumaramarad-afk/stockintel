import { ImageResponse } from "next/og";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#00d4aa",
          color: "#0a0a0f",
          fontSize: 14,
          fontWeight: 700,
        }}
      >
        GS
      </div>
    ),
    size,
  );
}
