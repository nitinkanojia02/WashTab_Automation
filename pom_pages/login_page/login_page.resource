*** Settings ***
Resource    ../../resources/common_keywords.resource

*** Variables ***
${USER_NAME_TEXTBOX}    xpath=//input[@placeholder='User Name']
${PASSWORD_TEXTBOX}    xpath=//input[@placeholder='Password']
${SIGN_IN_BUTTON}    xpath=//ion-button[normalize-space(.)='SIGN IN']
${VALID_USERNAME}    haklarr
${VALID_PASSWORD}    Icstunnel1
${INVALID_USERNAME}    invaliduser
${WRONG_USERNAME}    wronguser
${INVALID_PASSWORD}    WrongPassword
${LOWERCASE_PASSWORD}    icstunnel1
${USERNAME_UPPERCASE}    HAKLARR
${USERNAME_WITH_SPACES}    ${SPACE}haklarr${SPACE}
${PASSWORD_WITH_SPACES}    ${SPACE}Icstunnel1${SPACE}
${WHITESPACE_ONLY}    ${SPACE}${SPACE}${SPACE}
${SPECIAL_CHAR_USERNAME}    user!@#
${LONG_USERNAME}    verylongusernameinput_exceeding_expected_length_limit_for_testing_purposes_1234567890
${LONG_PASSWORD}    ExtremelyLongPasswordInput_For_UI_Boundary_Testing_1234567890_ABCDEFGHIJKLMNOPQRSTUVWXYZ
*** Keywords ***
Verify Login Page Loaded
    Wait For Element To Be Ready    ${USER_NAME_TEXTBOX}
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}

Enter User Name Textbox
    [Arguments]    ${text}
    Input Text When Ready    ${USER_NAME_TEXTBOX}    ${text}

Enter Password Textbox
    [Arguments]    ${text}
    Input Text When Ready    ${PASSWORD_TEXTBOX}    ${text}

Click Sign In Button
    Click When Ready    ${SIGN_IN_BUTTON}

Submit Login With Enter Key
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
    Press Keys    ${PASSWORD_TEXTBOX}    ENTER

Click Sign In Button Multiple Times
    Click When Ready    ${SIGN_IN_BUTTON}
    Click When Ready    ${SIGN_IN_BUTTON}
    Click When Ready    ${SIGN_IN_BUTTON}

Verify Login Rejected
    Wait For Element To Be Ready    ${USER_NAME_TEXTBOX}
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}

Verify Password Field Is Masked
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
    ${type}=    Get Element Attribute    ${PASSWORD_TEXTBOX}    type
    Should Be Equal    ${type}    password

Verify Login Page Still Displayed
    Wait For Element To Be Ready    ${USER_NAME_TEXTBOX}
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}
