import React from "react";
import blueTobyImg from "../../assets/keepers/blue-toby.png";

interface BlueTobyProps {
  size?: number;
  className?: string;
  alt?: string;
}

export const BlueToby: React.FC<BlueTobyProps> = ({
  size = 40,
  className = "",
  alt = "ToadAid Blue Toby",
}) => {
  return (
    <img
      src={blueTobyImg}
      alt={alt}
      width={size}
      height={size}
      className={`shrink-0 transition-transform select-none ${className}`}
      style={{
        objectFit: "contain",
        aspectRatio: "1 / 1",
        display: "block",
      }}
      loading="eager"
      decoding="async"
    />
  );
};
