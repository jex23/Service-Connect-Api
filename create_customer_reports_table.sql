-- Customer Reports/Complaints Table
-- Allows users to report issues with providers and services

CREATE TABLE IF NOT EXISTS customer_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    provider_id INT NOT NULL,
    provider_service_id INT NULL,
    booking_id INT NULL,
    report_type ENUM('service_quality', 'provider_behavior', 'payment_issue', 'cancellation', 'other') NOT NULL,
    subject VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    status ENUM('Pending', 'Under Review', 'Resolved', 'Rejected') NOT NULL DEFAULT 'Pending',
    admin_response TEXT NULL,
    admin_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,

    -- Foreign key constraints
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE,
    FOREIGN KEY (provider_service_id) REFERENCES provider_services(id) ON DELETE SET NULL,
    FOREIGN KEY (booking_id) REFERENCES service_booking(id) ON DELETE SET NULL,
    FOREIGN KEY (admin_id) REFERENCES admin(admin_id) ON DELETE SET NULL,

    -- Indexes for performance
    INDEX idx_user_id (user_id),
    INDEX idx_provider_id (provider_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_report_type (report_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add comment to table
ALTER TABLE customer_reports COMMENT = 'Stores customer complaints and reports about providers and services';
