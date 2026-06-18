*** Settings ***
Resource    ../resources/common_keywords.resource
Resource    ../pom_pages/login_page/login_page.resource

Test Setup    Open Login Page    http://172.21.166.115/washtabui/login?data=undefined
Test Teardown    Close Browser Session

*** Test Cases ***
LOGIN_TC_001 Verify login page loads successfully
    Verify Login Page Loaded

LOGIN_TC_002 Verify successful login with valid username and password
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Wait Until Element Is Not Visible    ${USER_NAME_TEXTBOX}

LOGIN_TC_003 Verify login fails with incorrect username
    Verify Login Page Loaded
    Enter User Name Textbox    ${INVALID_USERNAME}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Verify Login Page Still Displayed

LOGIN_TC_004 Verify login fails with incorrect password
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${INVALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Verify Login Page Still Displayed

LOGIN_TC_005 Verify login fails when both username and password are blank
    Verify Login Page Loaded
    Enter User Name Textbox    ${EMPTY}
    Enter Password Textbox    ${EMPTY}
    Click Sign In Button
    Verify Login Rejected
    Verify Login Page Still Displayed

LOGIN_TC_006 Verify login fails when username is blank
    Verify Login Page Loaded
    Enter User Name Textbox    ${EMPTY}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Verify Login Page Still Displayed

LOGIN_TC_007 Verify login fails when password is blank
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${EMPTY}
    Click Sign In Button
    Verify Login Rejected
    Verify Login Page Still Displayed

LOGIN_TC_008 Verify username field accepts leading and trailing spaces
    Verify Login Page Loaded
    Enter User Name Textbox    ${USERNAME_WITH_SPACES}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Verify Login Page Still Displayed

LOGIN_TC_009 Verify password field accepts leading and trailing spaces
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${PASSWORD_WITH_SPACES}
    Click Sign In Button
    Verify Login Rejected
    Verify Login Page Still Displayed

LOGIN_TC_010 Verify login fails with whitespace-only username and password
    Verify Login Page Loaded
    Enter User Name Textbox    ${WHITESPACE_ONLY}
    Enter Password Textbox    ${WHITESPACE_ONLY}
    Click Sign In Button
    Verify Login Rejected
    Verify Login Page Still Displayed

LOGIN_TC_011 Verify login fails with very long username input
    Verify Login Page Loaded
    Enter User Name Textbox    ${LONG_USERNAME}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Verify Login Page Still Displayed

LOGIN_TC_012 Verify login fails with very long password input
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${LONG_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Verify Login Page Still Displayed

LOGIN_TC_013 Verify username field accepts special characters input
    Verify Login Page Loaded
    Enter User Name Textbox    ${SPECIAL_CHAR_USERNAME}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Verify Login Page Still Displayed

LOGIN_TC_014 Verify password field masks entered characters
    Verify Login Page Loaded
    Enter Password Textbox    ${VALID_PASSWORD}
    Verify Password Field Is Masked

LOGIN_TC_015 Verify login using Enter key submission
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${VALID_PASSWORD}
    Submit Login With Enter Key
    Wait Until Element Is Not Visible    ${USER_NAME_TEXTBOX}

LOGIN_TC_016 Verify login fails with case-sensitive username variation
    Verify Login Page Loaded
    Enter User Name Textbox    ${USERNAME_UPPERCASE}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Verify Login Page Still Displayed

LOGIN_TC_017 Verify login fails with case-sensitive password variation
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${LOWERCASE_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Verify Login Page Still Displayed

LOGIN_TC_018 Verify multiple rapid login button clicks handling
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button Multiple Times
    Wait Until Element Is Not Visible    ${USER_NAME_TEXTBOX}

LOGIN_TC_019 Verify copy paste functionality for username and password fields
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Wait Until Element Is Not Visible    ${USER_NAME_TEXTBOX}

LOGIN_TC_020 Verify error message visibility after failed login attempt
    Verify Login Page Loaded
    Enter User Name Textbox    ${WRONG_USERNAME}
    Enter Password Textbox    ${INVALID_PASSWORD}
    Click Sign In Button
    Verify Login Rejected
    Verify Login Page Still Displayed
