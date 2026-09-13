-- ==========================================================
-- RETURNITY Database Schema
-- Lost and Found Management System
-- Normalized MySQL Schema for MCA Project
-- ==========================================================

CREATE DATABASE IF NOT EXISTS `returnity_db`
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE `returnity_db`;

-- Drop existing tables in reverse dependency order if resetting
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `notifications`;
DROP TABLE IF EXISTS `claim_audit_logs`;
DROP TABLE IF EXISTS `verification_results`;
DROP TABLE IF EXISTS `ownership_evidence`;
DROP TABLE IF EXISTS `claim_answers`;
DROP TABLE IF EXISTS `claims`;
DROP TABLE IF EXISTS `found_items`;
DROP TABLE IF EXISTS `lost_items`;
DROP TABLE IF EXISTS `categories`;
DROP TABLE IF EXISTS `users`;
SET FOREIGN_KEY_CHECKS = 1;

-- ----------------------------------------------------------
-- 1. Users Table
-- Stores credentials and user account information
-- ----------------------------------------------------------
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `full_name` VARCHAR(100) NOT NULL,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `phone` VARCHAR(20) DEFAULT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` ENUM('user', 'admin') NOT NULL DEFAULT 'user',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_users_email` (`email`),
    INDEX `idx_users_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 2. Categories Table
-- Standard item classification
-- ----------------------------------------------------------
CREATE TABLE `categories` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(80) NOT NULL UNIQUE,
    `description` VARCHAR(255) DEFAULT NULL,
    `icon` VARCHAR(50) NOT NULL DEFAULT 'box',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 3. Lost Items Table
-- Public information separated from private verification data
-- ----------------------------------------------------------
CREATE TABLE `lost_items` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `category_id` INT NOT NULL,
    `item_name` VARCHAR(150) NOT NULL,
    `description` TEXT NOT NULL,
    `date_lost` DATE NOT NULL,
    `approximate_time` VARCHAR(50) DEFAULT NULL,
    `location_lost` VARCHAR(200) NOT NULL,
    `safe_image_path` VARCHAR(255) DEFAULT NULL,
    `additional_info` TEXT DEFAULT NULL,
    -- Private Verification Information (Never revealed publicly or to claimants)
    `private_identifying_detail` TEXT NOT NULL,
    `private_distinctive_characteristic` TEXT DEFAULT NULL,
    `private_contents` TEXT DEFAULT NULL,
    `private_serial_or_id` VARCHAR(100) DEFAULT NULL,
    `private_exact_location` VARCHAR(200) DEFAULT NULL,
    `status` ENUM('Active', 'Claim Pending', 'Under Verification', 'Claimed', 'Returned', 'Closed') NOT NULL DEFAULT 'Active',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`category_id`) REFERENCES `categories`(`id`) ON DELETE RESTRICT,
    INDEX `idx_lost_status` (`status`),
    INDEX `idx_lost_category` (`category_id`),
    INDEX `idx_lost_date` (`date_lost`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 4. Found Items Table
-- Reports for items found by community members
-- ----------------------------------------------------------
CREATE TABLE `found_items` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `category_id` INT NOT NULL,
    `item_name` VARCHAR(150) NOT NULL,
    `description` TEXT NOT NULL,
    `date_found` DATE NOT NULL,
    `approximate_time` VARCHAR(50) DEFAULT NULL,
    `location_found` VARCHAR(200) NOT NULL,
    `safe_image_path` VARCHAR(255) DEFAULT NULL,
    `additional_info` TEXT DEFAULT NULL,
    `custody_location` VARCHAR(200) DEFAULT NULL,
    `private_finder_notes` TEXT DEFAULT NULL,
    `status` ENUM('Active', 'Claim Pending', 'Under Verification', 'Claimed', 'Returned', 'Closed') NOT NULL DEFAULT 'Active',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`category_id`) REFERENCES `categories`(`id`) ON DELETE RESTRICT,
    INDEX `idx_found_status` (`status`),
    INDEX `idx_found_category` (`category_id`),
    INDEX `idx_found_date` (`date_found`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 5. Claims Table
-- Verification requests submitted by claimants
-- ----------------------------------------------------------
CREATE TABLE `claims` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `item_type` ENUM('lost', 'found') NOT NULL,
    `item_id` INT NOT NULL,
    `claimant_id` INT NOT NULL,
    `status` ENUM('Pending Verification', 'Under Admin Review', 'Additional Information Required', 'Approved', 'Rejected', 'Closed') NOT NULL DEFAULT 'Pending Verification',
    `verification_score` INT NOT NULL DEFAULT 0,
    `confidence_level` ENUM('Strong Verification', 'Needs Review', 'Low Confidence') NOT NULL DEFAULT 'Needs Review',
    `suspicious_flag` TINYINT(1) NOT NULL DEFAULT 0,
    `suspicious_reasons` TEXT DEFAULT NULL,
    `additional_info_requested` TEXT DEFAULT NULL,
    `additional_info_provided` TEXT DEFAULT NULL,
    `admin_notes` TEXT DEFAULT NULL,
    `reviewed_by` INT DEFAULT NULL,
    `reviewed_at` DATETIME DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`claimant_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`reviewed_by`) REFERENCES `users`(`id`) ON DELETE SET NULL,
    INDEX `idx_claims_item` (`item_type`, `item_id`),
    INDEX `idx_claims_claimant` (`claimant_id`),
    INDEX `idx_claims_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 6. Claim Answers Table
-- Stores claimant's responses to ownership verification questions
-- ----------------------------------------------------------
CREATE TABLE `claim_answers` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `claim_id` INT NOT NULL,
    `question_key` VARCHAR(60) NOT NULL,
    `question_text` VARCHAR(255) NOT NULL,
    `answer_text` TEXT NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`claim_id`) REFERENCES `claims`(`id`) ON DELETE CASCADE,
    INDEX `idx_claim_answers_claim` (`claim_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 7. Ownership Evidence Table
-- Sensitive documents stored outside public webroot
-- ----------------------------------------------------------
CREATE TABLE `ownership_evidence` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `claim_id` INT NOT NULL,
    `file_path` VARCHAR(255) NOT NULL,
    `original_filename` VARCHAR(255) NOT NULL,
    `file_type` VARCHAR(50) NOT NULL,
    `description` VARCHAR(255) DEFAULT NULL,
    `uploaded_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`claim_id`) REFERENCES `claims`(`id`) ON DELETE CASCADE,
    INDEX `idx_evidence_claim` (`claim_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 8. Verification Results Table
-- Detailed decision support metrics for the administrator
-- ----------------------------------------------------------
CREATE TABLE `verification_results` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `claim_id` INT NOT NULL UNIQUE,
    `score` INT NOT NULL DEFAULT 0,
    `score_breakdown` TEXT NOT NULL,
    `confidence_level` VARCHAR(50) NOT NULL,
    `flags` TEXT DEFAULT NULL,
    `calculated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`claim_id`) REFERENCES `claims`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 9. Claim Audit Logs Table
-- Complete historical trail of all actions on claims and items
-- ----------------------------------------------------------
CREATE TABLE `claim_audit_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `claim_id` INT DEFAULT NULL,
    `item_type` VARCHAR(20) DEFAULT NULL,
    `item_id` INT DEFAULT NULL,
    `user_id` INT DEFAULT NULL,
    `action` VARCHAR(100) NOT NULL,
    `notes` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL,
    INDEX `idx_audit_claim` (`claim_id`),
    INDEX `idx_audit_action` (`action`),
    INDEX `idx_audit_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- 10. Notifications Table
-- User status alerts regarding claims and reports
-- ----------------------------------------------------------
CREATE TABLE `notifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `title` VARCHAR(150) NOT NULL,
    `message` TEXT NOT NULL,
    `link` VARCHAR(255) DEFAULT NULL,
    `is_read` TINYINT(1) NOT NULL DEFAULT 0,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_notifications_user` (`user_id`, `is_read`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------
-- Seed Initial Categories
-- ----------------------------------------------------------
INSERT INTO `categories` (`name`, `description`, `icon`) VALUES
('Electronics & Gadgets', 'Smartphones, laptops, headphones, chargers and accessories', 'device'),
('Wallets & Purses', 'Pocket wallets, coin pouches, cardholders and billfolds', 'wallet'),
('Keys & Keychains', 'Vehicle keys, home keys, lock combinations and keyrings', 'key'),
('Official Documents & IDs', 'Aadhaar, driving licenses, college IDs, passports and cards', 'document'),
('Bags & Backpacks', 'College bags, shoulder bags, suitcases and travel carriers', 'briefcase'),
('Jewelry & Watches', 'Wristwatches, finger rings, chains, bracelets and pendants', 'watch'),
('Clothing & Wearables', 'Jackets, mufflers, caps, athletic wear and umbrellas', 'tag'),
('Books & Study Material', 'Notebooks, textbooks, project files and binders', 'book'),
('Optical & Eyewear', 'Prescription glasses, sunglasses and protective cases', 'eye'),
('Miscellaneous', 'Other physical items not classified above', 'box');
