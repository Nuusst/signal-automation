#!/bin/bash

# Signal Automation Health Check Script
# Run this script via cron to monitor the service

SERVICE_NAME="signal-automation"
LOG_FILE="/opt/signal-automation/logs/health-check.log"
CRITICAL_LOG="/opt/signal-automation/logs/critical-errors.log"
ADMIN_PHONE="+33987654321"  # Update with actual admin phone
SIGNAL_NUMBER="+33123456789"  # Update with actual signal number
SERVICE_USER="signal-automation"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to send emergency alert (fallback when Signal service is down)
send_emergency_alert() {
    local message="$1"
    log_message "EMERGENCY: $message"
    
    # Try to send via signal-cli directly as service user
    if command -v signal-cli >/dev/null 2>&1; then
        sudo -u "$SERVICE_USER" signal-cli -a "$SIGNAL_NUMBER" send "$ADMIN_PHONE" -m "🚨 HEALTH CHECK ALERT: $message" 2>/dev/null
    fi
    
    # You can add additional alert methods here (email, webhook, etc.)
}

# Check if service is running
check_service_status() {
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        return 0
    else
        return 1
    fi
}

# Check if there are recent critical errors
check_critical_errors() {
    if [ -f "$CRITICAL_LOG" ]; then
        # Check for critical errors in the last 5 minutes
        recent_errors=$(find "$CRITICAL_LOG" -newermt "5 minutes ago" -exec grep -c "CRITICAL\|ERROR" {} \; 2>/dev/null || echo "0")
        if [ "$recent_errors" -gt 0 ]; then
            return 1
        fi
    fi
    return 0
}

# Check database connectivity
check_database() {
    # Simple check - try to connect to MySQL
    if ! mysqladmin ping -h localhost -u signal_automation --silent 2>/dev/null; then
        return 1
    fi
    return 0
}

# Check disk space
check_disk_space() {
    # Check if /opt/signal-automation has less than 100MB free
    available=$(df /opt/signal-automation | tail -1 | awk '{print $4}')
    if [ "$available" -lt 102400 ]; then  # 100MB in KB
        return 1
    fi
    return 0
}

# Main health check
main() {
    log_message "Starting health check"
    
    # Check service status
    if ! check_service_status; then
        send_emergency_alert "Service $SERVICE_NAME is not running"
        log_message "ERROR: Service is not running"
        
        # Attempt to restart
        log_message "Attempting to restart service"
        if systemctl restart "$SERVICE_NAME"; then
            log_message "Service restarted successfully"
            sleep 5
            if check_service_status; then
                send_emergency_alert "Service $SERVICE_NAME was restarted successfully"
            else
                send_emergency_alert "Failed to restart service $SERVICE_NAME"
            fi
        else
            send_emergency_alert "Failed to restart service $SERVICE_NAME"
        fi
        exit 1
    fi
    
    # Check for critical errors
    if ! check_critical_errors; then
        send_emergency_alert "Critical errors detected in the last 5 minutes"
        log_message "WARNING: Critical errors detected"
    fi
    
    # Check database connectivity
    if ! check_database; then
        send_emergency_alert "Database connectivity issues detected"
        log_message "ERROR: Database connectivity issues"
    fi
    
    # Check disk space
    if ! check_disk_space; then
        send_emergency_alert "Low disk space detected"
        log_message "WARNING: Low disk space"
    fi
    
    log_message "Health check completed successfully"
}

# Run main function
main "$@"
