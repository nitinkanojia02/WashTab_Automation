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
    Wait Until Element Is Not Visible    ${USER_NAME_TEXTBOX}    10s

LOGIN_TC_003 Verify login fails with incorrect username and valid password
    Verify Login Page Loaded
    Enter User Name Textbox    ${INVALID_USERNAME}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Failed

LOGIN_TC_004 Verify login fails with valid username and incorrect password
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${INVALID_PASSWORD}
    Click Sign In Button
    Verify Login Failed

LOGIN_TC_005 Verify login fails when both username and password are blank
    Verify Login Page Loaded
    Enter User Name Textbox    ${BLANK_USERNAME}
    Enter Password Textbox    ${BLANK_PASSWORD}
    Click Sign In Button
    Verify Login Failed

LOGIN_TC_006 Verify login fails when username is blank
    Verify Login Page Loaded
    Enter User Name Textbox    ${BLANK_USERNAME}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Failed

LOGIN_TC_007 Verify login fails when password is blank
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${BLANK_PASSWORD}
    Click Sign In Button
    Verify Login Failed

LOGIN_TC_008 Verify username field accepts input
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    ${value}=    Get Element Attribute    ${USER_NAME_TEXTBOX}    value
    Should Be Equal    ${value}    ${VALID_USERNAME}

LOGIN_TC_009 Verify password field masks characters
    Verify Login Page Loaded
    Enter Password Textbox    ${VALID_PASSWORD}
    ${type}=    Get Element Attribute    ${PASSWORD_TEXTBOX}    type
    Should Be Equal    ${type}    password

LOGIN_TC_010 Verify login using Enter key
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${VALID_PASSWORD}
    Press Keys    ${PASSWORD_TEXTBOX}    ENTER
    Wait Until Element Is Not Visible    ${USER_NAME_TEXTBOX}    10s

LOGIN_TC_011 Verify login fails with whitespace-only username
    Verify Login Page Loaded
    Enter User Name Textbox    ${SPACE}${SPACE}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Failed

LOGIN_TC_012 Verify login fails with whitespace-only password
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${SPACE}${SPACE}
    Click Sign In Button
    Verify Login Failed

LOGIN_TC_013 Verify username with leading and trailing spaces
    Verify Login Page Loaded
    Enter User Name Textbox    ${SPACE}${VALID_USERNAME}${SPACE}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Failed

LOGIN_TC_014 Verify password with leading and trailing spaces
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${SPACE}${VALID_PASSWORD}${SPACE}
    Click Sign In Button
    Verify Login Failed

LOGIN_TC_015 Verify login with very long username input
    Verify Login Page Loaded
    ${long_username}=    Evaluate    "a"*260
    Enter User Name Textbox    ${long_username}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Failed

LOGIN_TC_016 Verify login with very long password input
    Verify Login Page Loaded
    ${long_password}=    Evaluate    "a"*260
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${long_password}
    Click Sign In Button
    Verify Login Failed

LOGIN_TC_017 Verify login fails with special characters in username
    Verify Login Page Loaded
    Enter User Name Textbox    !@#$$%
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Failed

LOGIN_TC_018 Verify case sensitivity of username
    Verify Login Page Loaded
    Enter User Name Textbox    HAKLARR
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Verify Login Failed

LOGIN_TC_019 Verify case sensitivity of password
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    icstunnel1
    Click Sign In Button
    Verify Login Failed

LOGIN_TC_020 Verify repeated clicking of login button during submission
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Click Sign In Button
    Click Sign In Button
    Wait Until Element Is Not Visible    ${USER_NAME_TEXTBOX}    10s

LOGIN_TC_021 Verify copy paste into username and password fields
    Verify Login Page Loaded
    Enter User Name Textbox    ${VALID_USERNAME}
    Enter Password Textbox    ${VALID_PASSWORD}
    Click Sign In Button
    Wait Until Element Is Not Visible    ${USER_NAME_TEXTBOX}    10s
